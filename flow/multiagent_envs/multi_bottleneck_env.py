"""
Environments for training vehicles to reduce capacity drops in a bottleneck.
This environment was used in:
TODO(ak): add paper after it has been published.
"""

from copy import deepcopy

from flow.controllers.rlcontroller import RLController
from flow.controllers.routing_controllers import ContinuousRouter
from flow.controllers.lane_change_controllers import SimLaneChangeController
from flow.multiagent_envs.multiagent_env import MultiEnv
from flow.envs.bottleneck_env import DesiredVelocityEnv
from flow.core.params import InFlows, NetParams, VehicleParams, \
    SumoCarFollowingParams, SumoLaneChangeParams

import numpy as np
from gym.spaces.box import Box
from gym.spaces.discrete import Discrete
from gym.spaces.tuple_space import Tuple

MAX_LANES = 4  # base number of largest number of lanes in the network
EDGE_LIST = ["1", "2", "3", "4", "5"]  # Edge 1 is before the toll booth

# Keys for RL experiments
ADDITIONAL_RL_ENV_PARAMS = {
    # velocity to use in reward functions
    "target_velocity": 30,
    # if an RL vehicle exits, place it back at the front
    "add_rl_if_exit": True,
    # whether communication between vehicles is on
    "communicate": False,
    # whether the observation space is aggregate counts or local observations
    "centralized_obs": False,
    # whether to add aggregate info (speed, number of congested vehicles) about some of the edges
    "aggregate_info": False,
    # whether to add an additional penalty for allowing too many vehicles into the bottleneck
    "congest_penalty": False,
    "av_frac": 0.1,
    # Above this number, the congestion penalty starts to kick in
    "congest_penalty_start": 30,
    # What lane changing mode the human drivers should have
    "lc_mode": 0
}


class MultiBottleneckEnv(MultiEnv, DesiredVelocityEnv):
    """Environment used to train decentralized vehicles to effectively pass
       through a bottleneck by specifying the velocity that RL vehicles
       should attempt to travel in certain regions of space
       States
           An observation is the speed and velocity of leading and
           following vehicles
       Actions
           The action space consist of a dict of accelerations for each
           autonomous vehicle
       Rewards
           The reward is a dict consisting of the normalized
           outflow of the bottleneck
    """

    @property
    def observation_space(self):
        """See class definition."""

        # normalized speed and velocity of leading and following vehicles
        # additionally, for each lane leader we add if it is
        # an RL vehicle or not
        # the position edge id, and lane of the vehicle
        # additionally, we add the time-step (for the baseline)
        # the outflow over the last 10 seconds
        # the number of vehicles in the congested section
        # the average velocity on each edge 3,4,5
        add_params = self.env_params.additional_params
        if add_params['centralized_obs']:
            num_obs = 0
            # density and velocity for rl and non-rl vehicles per segment
            # Last element is the outflow and inflow
            for segment in self.obs_segments:
                num_obs += 4 * segment[1] * \
                           self.k.scenario.num_lanes(segment[0])
            num_obs += 2
            return Box(low=-3.0, high=3.0, shape=(num_obs,), dtype=np.float32)
        else:
            if self.env_params.additional_params.get('communicate', False):
                # eight possible signals if above
                if self.env_params.additional_params.get('aggregate_info'):
                    return Box(low=-3.0, high=3.0,
                               shape=(6 * MAX_LANES * self.scaling + 17,),
                               dtype=np.float32)
                else:
                    return Box(low=-3.0, high=3.0,
                               shape=(6 * MAX_LANES * self.scaling + 11,),
                               dtype=np.float32)
            else:
                if self.env_params.additional_params.get('aggregate_info'):
                    return Box(low=-3.0, high=3.0,
                               shape=(6 * MAX_LANES * self.scaling + 9,),
                               dtype=np.float32)
                else:
                    return Box(low=-3.0, high=3.0,
                               shape=(6 * MAX_LANES * self.scaling + 3,),
                               dtype=np.float32)

    @property
    def action_space(self):
        """See class definition."""
        if self.env_params.additional_params.get('communicate', False):
            accel = Box(
                low=-1.5, high=1.0, shape=(1,), dtype=np.float32)
            communicate = Discrete(2)
            return Tuple((accel, communicate))
        else:
            return Box(
                low=-1.5, high=1.0, shape=(1,), dtype=np.float32)

    def get_state(self, rl_actions=None):
        """See class definition."""
        # action space is speed and velocity of leading and following
        # vehicles for all of the avs
        add_params = self.env_params.additional_params
        if add_params['centralized_obs']:
            rl_ids = self.k.vehicle.get_rl_ids()
            state = self.get_centralized_state()
            veh_info = {rl_id: state for rl_id in rl_ids}
            left_vehicles_dict = {veh_id: np.zeros(self.observation_space.shape[0]) for veh_id
                                  in self.k.vehicle.get_arrived_ids() if veh_id in self.k.vehicle.get_rl_ids()}
            veh_info.update(left_vehicles_dict)
        else:
            if self.env_params.additional_params.get('communicate', False):
                veh_info = {rl_id: np.concatenate((self.state_util(rl_id),
                                                   self.veh_statistics(rl_id),
                                                   self.get_signal(rl_id,
                                                                   rl_actions)
                                                   )
                                                  )
                            for rl_id in self.k.vehicle.get_rl_ids()}
            else:
                veh_info = {rl_id: np.concatenate((self.state_util(rl_id),
                                                   self.veh_statistics(rl_id)))
                            for rl_id in self.k.vehicle.get_rl_ids()}
            if self.env_params.additional_params.get('aggregate_info'):
                agg_statistics = self.aggregate_statistics()
                veh_info = {rl_id: np.concatenate((val, agg_statistics))
                                     for rl_id, val in veh_info.items()}
            # Go through the human drivers and add zeros if the vehicles have left as a final observation
            left_vehicles_dict = {veh_id: np.zeros(self.observation_space.shape[0]) for veh_id
                                  in self.k.vehicle.get_arrived_ids() if veh_id in self.k.vehicle.get_rl_ids()}
            veh_info.update(left_vehicles_dict)

        return veh_info

    def get_centralized_state(self):
        """See class definition."""
        # action space is number of vehicles in each segment in each lane,
        # number of rl vehicles in each segment in each lane
        # mean speed in each segment, and mean rl speed in each
        # segment in each lane
        num_vehicles_list = []
        num_rl_vehicles_list = []
        vehicle_speeds_list = []
        rl_speeds_list = []
        NUM_VEHICLE_NORM = 20
        for i, edge in enumerate(EDGE_LIST):
            num_lanes = self.k.scenario.num_lanes(edge)
            num_vehicles = np.zeros((self.num_obs_segments[i], num_lanes))
            num_rl_vehicles = np.zeros((self.num_obs_segments[i], num_lanes))
            vehicle_speeds = np.zeros((self.num_obs_segments[i], num_lanes))
            rl_vehicle_speeds = np.zeros((self.num_obs_segments[i], num_lanes))
            ids = self.k.vehicle.get_ids_by_edge(edge)
            lane_list = self.k.vehicle.get_lane(ids)
            pos_list = self.k.vehicle.get_position(ids)
            for i, id in enumerate(ids):
                segment = np.searchsorted(self.obs_slices[edge],
                                          pos_list[i]) - 1
                if id in self.k.vehicle.get_rl_ids():
                    rl_vehicle_speeds[segment, lane_list[i]] \
                        += self.k.vehicle.get_speed(id)
                    num_rl_vehicles[segment, lane_list[i]] += 1
                else:
                    vehicle_speeds[segment, lane_list[i]] \
                        += self.k.vehicle.get_speed(id)
                    num_vehicles[segment, lane_list[i]] += 1

            # normalize

            num_vehicles /= NUM_VEHICLE_NORM
            num_rl_vehicles /= NUM_VEHICLE_NORM
            num_vehicles_list += num_vehicles.flatten().tolist()
            num_rl_vehicles_list += num_rl_vehicles.flatten().tolist()
            vehicle_speeds_list += vehicle_speeds.flatten().tolist()
            rl_speeds_list += rl_vehicle_speeds.flatten().tolist()

        unnorm_veh_list = np.asarray(num_vehicles_list) * \
            NUM_VEHICLE_NORM
        unnorm_rl_list = np.asarray(num_rl_vehicles_list) * \
            NUM_VEHICLE_NORM
        # compute the mean speed if the speed isn't zero
        num_rl = len(num_rl_vehicles_list)
        num_veh = len(num_vehicles_list)
        mean_speed = np.nan_to_num([
            vehicle_speeds_list[i] / unnorm_veh_list[i]
            if int(unnorm_veh_list[i]) else 0 for i in range(num_veh)
        ])
        mean_speed_norm = mean_speed / 50
        mean_rl_speed = np.nan_to_num([
            rl_speeds_list[i] / unnorm_rl_list[i]
            if int(unnorm_rl_list[i]) else 0 for i in range(num_rl)
        ]) / 50
        outflow = np.asarray(
            self.k.vehicle.get_outflow_rate(20 * self.sim_step) / 2000.0)
        return np.concatenate((num_vehicles_list, num_rl_vehicles_list,
                               mean_speed_norm, mean_rl_speed, [outflow],
                               [self.inflow]))

    def _apply_rl_actions(self, rl_actions):
        """
        RL actions are split up into 3 levels.
        First, they're split into edge actions.
        Then they're split into segment actions.
        Then they're split into lane actions.
        """
        if rl_actions:
            rl_ids = list(rl_actions.keys())
            actions = list(rl_actions.values())
            if self.env_params.additional_params.get('communicate', False):
                accel = np.concatenate([action[0] for action in actions])
            else:
                accel = actions
            self.k.vehicle.apply_acceleration(rl_ids, accel)

    def compute_reward(self, rl_actions, **kwargs):
        """Outflow rate over last ten seconds normalized to max of 1."""

        if self.env_params.evaluate:
            if self.time_counter == self.env_params.horizon:
                reward = self.k.vehicle.get_outflow_rate(500)
                return reward
            else:
                return 0

        reward = self.k.vehicle.get_outflow_rate(10 * self.sim_step) / \
                 (2000.0 * self.scaling) - 3
        if self.env_params.additional_params["congest_penalty"]:
            num_vehs = len(self.k.vehicle.get_ids_by_edge('4'))
            if num_vehs > 30 * self.scaling:
                penalty = (num_vehs - 30 * self.scaling) / 10.0
                reward -= penalty
        reward_dict = {rl_id: reward for rl_id in self.k.vehicle.get_rl_ids()}
        # If a vehicle has left, just make sure to return a reward for it
        left_vehicles_dict = {veh_id: 0 for veh_id
                              in self.k.vehicle.get_arrived_ids() if veh_id in self.k.vehicle.get_rl_ids()}
        reward_dict.update(left_vehicles_dict)
        return reward_dict

    def reset(self, new_inflow_rate=None):
        add_params = self.env_params.additional_params
        if add_params.get("reset_inflow"):
            inflow_range = add_params.get("inflow_range")
            if new_inflow_rate:
                flow_rate = new_inflow_rate
            else:
                flow_rate = np.random.uniform(
                    min(inflow_range), max(inflow_range)) * self.scaling
            self.inflow = flow_rate
            print('THE FLOW RATE IS: ', flow_rate)
            for _ in range(100):
                try:
                    vehicles = VehicleParams()
                    if not np.isclose(add_params.get("av_frac"), 1):
                        vehicles.add(
                            veh_id="human",
                            lane_change_controller=(SimLaneChangeController, {}),
                            routing_controller=(ContinuousRouter, {}),
                            car_following_params=SumoCarFollowingParams(
                                speed_mode=31,
                            ),
                            lane_change_params=SumoLaneChangeParams(
                                lane_change_mode=add_params.get("lc_mode"),
                            ),
                            num_vehicles=1)
                        vehicles.add(
                            veh_id="av",
                            acceleration_controller=(RLController, {}),
                            lane_change_controller=(SimLaneChangeController, {}),
                            routing_controller=(ContinuousRouter, {}),
                            car_following_params=SumoCarFollowingParams(
                                speed_mode=31,
                            ),
                            lane_change_params=SumoLaneChangeParams(
                                lane_change_mode=0,
                            ),
                            num_vehicles=1)
                    else:
                        vehicles.add(
                            veh_id="av",
                            acceleration_controller=(RLController, {}),
                            lane_change_controller=(SimLaneChangeController, {}),
                            routing_controller=(ContinuousRouter, {}),
                            car_following_params=SumoCarFollowingParams(
                                speed_mode=31,
                            ),
                            lane_change_params=SumoLaneChangeParams(
                                lane_change_mode=add_params.get("lc_mode"),
                            ),
                            num_vehicles=1)

                    inflow = InFlows()
                    if not np.isclose(add_params.get("av_frac"), 1.0):
                        inflow.add(
                            veh_type="av",
                            edge="1",
                            vehs_per_hour=flow_rate * add_params.get("av_frac"),
                            departLane="random",
                            departSpeed=10.0)
                        inflow.add(
                            veh_type="human",
                            edge="1",
                            vehs_per_hour=flow_rate * (1 - add_params.get("av_frac")),
                            departLane="random",
                            departSpeed=10.0)
                    else:
                        inflow.add(
                            veh_type="av",
                            edge="1",
                            vehs_per_hour=flow_rate,
                            departLane="random",
                            departSpeed=10.0)

                    additional_net_params = {
                        "scaling": self.scaling,
                        "speed_limit": self.scenario.net_params.
                        additional_params['speed_limit']
                    }
                    net_params = NetParams(
                        inflows=inflow,
                        no_internal_links=False,
                        additional_params=additional_net_params)

                    self.scenario = self.scenario.__class__(
                        self.scenario.orig_name, vehicles,
                        net_params, self.scenario.initial_config)
                    self.k.vehicle = deepcopy(self.initial_vehicles)
                    self.k.vehicle.kernel_api = self.k.kernel_api
                    self.k.vehicle.master_kernel = self.k

                    # restart the sumo instance
                    self.restart_simulation(
                        sim_params=self.sim_params,
                        render=self.sim_params.render)

                    observation = super().reset()

                    # reset the timer to zero
                    self.time_counter = 0

                    return observation

                except Exception as e:
                    print('error on reset ', e)

        # perform the generic reset function
        observation = super().reset()

        # reset the timer to zero
        self.time_counter = 0

        return observation

    def veh_statistics(self, rl_id):
        '''Returns speed and edge information about the vehicle itself'''
        speed = self.k.vehicle.get_speed(rl_id)/100.0
        edge = self.k.vehicle.get_edge(rl_id)
        lane = (self.k.vehicle.get_lane(rl_id)+1)/10.0
        if edge:
            if edge[0] != ':':
                edge_id = int(self.k.vehicle.get_edge(rl_id))/10.0
            else:
                edge_id = - 1 / 10.0
        else:
            edge_id = - 1/10.0
        return np.array([speed, edge_id, lane])

    def state_util(self, rl_id):
        ''' Returns an array of headway, tailway, leader speed, follower speed
            a 1 if leader is rl 0 otherwise, a 1 if follower is rl 0
            otherwise
            If there are fewer than self.scaling*MAX_LANES the extra
            entries are filled with -1 to disambiguate from zeros
        '''
        veh = self.k.vehicle
        lane_headways = veh.get_lane_headways(rl_id).copy()
        lane_tailways = veh.get_lane_tailways(rl_id).copy()
        lane_leader_speed = veh.get_lane_leaders_speed(rl_id).copy()
        lane_follower_speed = veh.get_lane_followers_speed(rl_id).copy()
        leader_ids = veh.get_lane_leaders(rl_id).copy()
        follower_ids = veh.get_lane_followers(rl_id).copy()
        rl_ids = self.k.vehicle.get_rl_ids()
        is_leader_rl = [1 if l_id in rl_ids else 0 for l_id in leader_ids]
        is_follow_rl = [1 if f_id in rl_ids else 0 for f_id in follower_ids]
        diff = self.scaling*MAX_LANES - len(is_leader_rl)
        if diff > 0:
            # the minus 1 disambiguates missing cars from missing lanes
            lane_headways += diff*[-1]
            lane_tailways += diff*[-1]
            lane_leader_speed += diff*[-1]
            lane_follower_speed += diff*[-1]
            is_leader_rl += diff*[-1]
            is_follow_rl += diff*[-1]
        lane_headways = np.asarray(lane_headways)/1000
        lane_tailways = np.asarray(lane_tailways)/1000
        lane_leader_speed = np.asarray(lane_leader_speed)/100
        lane_follower_speed = np.asarray(lane_follower_speed)/100
        return np.concatenate((lane_headways, lane_tailways, lane_leader_speed,
                               lane_follower_speed, is_leader_rl,
                               is_follow_rl))

    def aggregate_statistics(self):
        ''' Returns the time-step, outflow over the last 10 seconds,
            number of vehicles in the congested area
            and average velocity of segments 3,4,5,6
        '''
        time_step = self.time_counter/self.env_params.horizon
        outflow = self.k.vehicle.get_outflow_rate(10)/3600
        valid_edges = ['3', '4', '5']
        congest_number = len(self.k.vehicle.get_ids_by_edge('4'))/50
        avg_speeds = np.zeros(len(valid_edges))
        for i, edge in enumerate(valid_edges):
            edge_veh = self.k.vehicle.get_ids_by_edge(edge)
            if len(edge_veh) > 0:
                veh = self.k.vehicle
                avg_speeds[i] = np.mean(veh.get_speed(edge_veh))/100.0
        return np.concatenate(([time_step], [outflow],
                               [congest_number], avg_speeds))

    def get_signal(self, rl_id, rl_actions):
        ''' Returns the communication signals that should be
            pass to the autonomous vehicles
        '''
        lead_ids = self.k.vehicle.get_lane_leaders(rl_id)
        follow_ids = self.k.vehicle.get_lane_followers(rl_id)
        comm_ids = lead_ids + follow_ids
        if rl_actions:
            signals = [rl_actions[av_id][1]/4.0 if av_id in
                       rl_actions.keys() else -1/4.0 for av_id in comm_ids]
            if len(signals) < 8:
                # the -2 disambiguates missing cars from missing lanes
                signals += (8-len(signals)) * [-2/4.0]
            return signals
        else:
            return [-1/4.0 for _ in range(8)]
