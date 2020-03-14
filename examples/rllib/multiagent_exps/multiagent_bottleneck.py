"""Multi-agent Bottleneck example.
In this example, the actions are accelerations for all of the agents.
The agents all share a single model.
"""
from datetime import datetime
import json

import pytz
import ray
import ray.rllib.agents.ppo as ppo
from ray import tune
from ray.rllib.agents.ppo.ppo_policy_graph import PPOPolicyGraph
from ray.tune import run_experiments
from ray.tune.registry import register_env

from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder
from flow.core.params import SumoParams, EnvParams, InitialConfig, NetParams, \
    InFlows, SumoLaneChangeParams, SumoCarFollowingParams
from flow.core.params import TrafficLightParams
from flow.core.params import VehicleParams
from flow.controllers import RLController, ContinuousRouter, \
    SimLaneChangeController

# time horizon of a single rollout
HORIZON = 2000
# number of parallel workers
N_CPUS = 1
# number of rollouts per training iteration
N_ROLLOUTS = 2*N_CPUS

SCALING = 1
NUM_LANES = 4 * SCALING  # number of lanes in the widest highway
DISABLE_TB = True
DISABLE_RAMP_METER = True
AV_FRAC = 0.10

vehicles = VehicleParams()
vehicles.add(
    veh_id='human',
    lane_change_controller=(SimLaneChangeController, {}),
    routing_controller=(ContinuousRouter, {}),
    car_following_params=SumoCarFollowingParams(
                            speed_mode=9,
                        ),
    lane_change_params=SumoLaneChangeParams(
                            lane_change_mode=0,
                        ),
    num_vehicles=1 * SCALING)
vehicles.add(
    veh_id='av',
    acceleration_controller=(RLController, {}),
    lane_change_controller=(SimLaneChangeController, {}),
    routing_controller=(ContinuousRouter, {}),
    car_following_params=SumoCarFollowingParams(
        speed_mode=9,
    ),
    lane_change_params=SumoLaneChangeParams(
        lane_change_mode=0,
    ),
    num_vehicles=1 * SCALING)

# flow rate
flow_rate = 1900 * SCALING

controlled_segments = [('1', 1, False), ('2', 2, True), ('3', 2, True),
                       ('4', 2, True), ('5', 1, False)]
num_observed_segments = [('1', 1), ('2', 3), ('3', 3), ('4', 3), ('5', 1)]
additional_env_params = {
    'target_velocity': 40,
    'disable_tb': True,
    'disable_ramp_metering': True,
    'controlled_segments': controlled_segments,
    'symmetric': False,
    'observed_segments': num_observed_segments,
    'reset_inflow': True,
    'lane_change_duration': 5,
    'max_accel': 3,
    'max_decel': 3,
    'inflow_range': [800, 3000],
    'start_inflow': flow_rate,
    'congest_penalty': False,
    'communicate': False,
    "centralized_obs": False
}

# percentage of flow coming out of each lane
inflow = InFlows()
inflow.add(
    veh_type='human',
    edge='1',
    vehs_per_hour=flow_rate * (1 - AV_FRAC),
    departLane='random',
    departSpeed=10.0)
inflow.add(
    veh_type='av',
    edge='1',
    vehs_per_hour=flow_rate * AV_FRAC,
    departLane='random',
    departSpeed=10.0)

traffic_lights = TrafficLightParams()
if not DISABLE_TB:
    traffic_lights.add(node_id='2')
if not DISABLE_RAMP_METER:
    traffic_lights.add(node_id='3')

additional_net_params = {'scaling': SCALING, "speed_limit": 23.0}
net_params = NetParams(
    inflows=inflow,
    no_internal_links=False,
    additional_params=additional_net_params)

flow_params = dict(
    # name of the experiment
    exp_tag='MultiDecentralObsBottleneck',

    # name of the flow environment the experiment is running on
    env_name='MultiBottleneckEnv',

    # name of the scenario class the experiment is running on
    scenario='BottleneckScenario',

    # simulator that is used by the experiment
    simulator='traci',

    # sumo-related parameters (see flow.core.params.SumoParams)
    sim=SumoParams(
        sim_step=0.5,
        render=False,
        print_warnings=False,
        restart_instance=True,
    ),

    # environment related parameters (see flow.core.params.EnvParams)
    env=EnvParams(
        warmup_steps=40,
        sims_per_step=1,
        horizon=HORIZON,
        additional_params=additional_env_params,
    ),

    # network-related parameters (see flow.core.params.NetParams and the
    # scenario's documentation or ADDITIONAL_NET_PARAMS component)
    net=NetParams(
        inflows=inflow,
        no_internal_links=False,
        additional_params=additional_net_params,
    ),

    # vehicles to be placed in the network at the start of a rollout (see
    # flow.core.vehicles.Vehicles)
    veh=vehicles,

    # parameters specifying the positioning of vehicles upon initialization/
    # reset (see flow.core.params.InitialConfig)
    initial=InitialConfig(
        spacing='uniform',
        min_gap=5,
        lanes_distribution=float('inf'),
        edges_distribution=['2', '3', '4', '5'],
    ),

    # traffic lights to be introduced to specific nodes (see
    # flow.core.traffic_lights.TrafficLights)
    tls=traffic_lights,
)


def setup_exps():
    alg_run = 'PPO'
    config = ppo.DEFAULT_CONFIG.copy()
    config['num_workers'] = N_CPUS
    config['train_batch_size'] = HORIZON * N_ROLLOUTS
    config['gamma'] = 0.999  # discount rate
    config['model'].update({'fcnet_hiddens': [100, 50, 25]})
    config['clip_actions'] = False
    config['horizon'] = HORIZON
    # config['use_centralized_vf'] = tune.grid_search([True, False])
    config['simple_optimizer'] = True

    # Grid search things
    # config['lr'] = tune.grid_search([5e-4, 5e-5])
    # config['num_sgd_iter'] = tune.grid_search([10, 30])

    # LSTM Things
    # config['model']['use_lstm'] = True
    # config['model']["max_seq_len"] = tune.grid_search([5, 10])
    # config['model']["lstm_cell_size"] = 256

    # save the flow params for replay
    flow_json = json.dumps(
        flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    create_env, env_name = make_create_env(params=flow_params, version=0)

    # Register as rllib env
    register_env(env_name, create_env)

    test_env = create_env()
    obs_space = test_env.observation_space
    act_space = test_env.action_space

    # Setup PG with an ensemble of `num_policies` different policy graphs
    policy_graphs = {'av': (PPOPolicyGraph, obs_space, act_space, {})}

    def policy_mapping_fn(agent_id):
        return 'av'

    config.update({
        'multiagent': {
            'policy_graphs': policy_graphs,
            'policy_mapping_fn': tune.function(policy_mapping_fn),
            "policies_to_train": ["av"]
        }
    })
    return alg_run, env_name, config


def on_episode_end(info):
    import ipdb; ipdb.set_trace()
    env = info['env'].get_unwrapped()[0]
    total_outflow = env.k.vehicle.get_outflow_rate(500)
    inflow = env.inflow
    # round it to 100
    inflow = int(inflow / 100) * 100
    episode = info["episode"]
    episode.custom_metrics["net_outflow_{}".format(inflow)] = total_outflow


if __name__ == '__main__':
    alg_run, env_name, config = setup_exps()
    # ray.init(redis_address='localhost:6379')
    ray.init(num_cpus=4, redirect_output=False)
    eastern = pytz.timezone('US/Eastern')
    date = datetime.now(tz=pytz.utc)
    date = date.astimezone(pytz.timezone('US/Pacific')).strftime("%m-%d-%Y")
    s3_string = "s3://eugene.experiments/old_bottleneck_test/" \
                + date + '/' + flow_params["exp_tag"]
    run_experiments({
        flow_params["exp_tag"]: {
            'run': alg_run,
            'env': env_name,
            'checkpoint_freq': 50,
            'stop': {
                'training_iteration': 500
            },
            'config': config,
            # 'upload_dir': s3_string
            'num_samples': 1,
            # "callbacks": {
            #     "on_episode_end": tune.function(on_episode_end),
            # },
        },
    })
