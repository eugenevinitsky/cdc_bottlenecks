"""Multi-agent Bottleneck example.
In this example, the actions are accelerations for all of the agents.
The agents all share a single model.
"""
from copy import deepcopy
from datetime import datetime
import errno
import json
import subprocess
import os

import pytz
import ray
import ray.rllib.agents.ppo as ppo
from ray.rllib.agents.ppo.ppo_policy_graph import PPOPolicyGraph
from ray import tune
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
from flow.multiagent_envs.multi_bottleneck_env import MultiBottleneckEnv
from flow.networks.bottleneck import BottleneckNetwork
from flow.utils.parsers import get_multiagent_bottleneck_parser
# from flow.visualize.bottleneck_results import run_bottleneck_results

def setup_exps(args):

    # time horizon of a single rollout
    HORIZON = args.horizon
    # number of parallel workers
    N_CPUS = args.num_cpus
    # number of rollouts per training iteration
    N_ROLLOUTS = args.num_cpus * args.rollout_scale_factor

    SCALING = 1
    DISABLE_TB = True
    DISABLE_RAMP_METER = True
    AV_FRAC = args.av_frac
    LC_MODE = args.lc_on

    vehicles = VehicleParams()
    vehicles.add(
        veh_id='human',
        lane_change_controller=(SimLaneChangeController, {}),
        routing_controller=(ContinuousRouter, {}),
        car_following_params=SumoCarFollowingParams(
                                speed_mode=9,
                            ),
        lane_change_params=SumoLaneChangeParams(
                                lane_change_mode=LC_MODE,
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
            lane_change_mode=LC_MODE,
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
        'inflow_range': [args.low_inflow, args.high_inflow],
        'start_inflow': flow_rate,
        'congest_penalty': args.congest_penalty,
        'communicate': args.communicate,
        "centralized_obs": args.central_obs,
        "av_frac": AV_FRAC,
        "lc_mode": LC_MODE,
        "num_curr_iters": args.num_curr_iters,
        "curriculum": args.curriculum
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

    flow_params = dict(
        # name of the experiment
        exp_tag='MultiDecentralObsBottleneck',

        # name of the flow environment the experiment is running on
        env_name=MultiBottleneckEnv,

        # name of the scenario class the experiment is running on
        network=BottleneckNetwork,

        # simulator that is used by the experiment
        simulator='traci',

        # sumo-related parameters (see flow.core.params.SumoParams)
        sim=SumoParams(
            sim_step=0.5,
            render=args.render,
            print_warnings=False,
            restart_instance=True,
        ),

        # environment related parameters (see flow.core.params.EnvParams)
        env=EnvParams(
            warmup_steps=0,
            sims_per_step=1,
            horizon=HORIZON,
            additional_params=additional_env_params,
        ),

        # network-related parameters (see flow.core.params.NetParams and the
        # scenario's documentation or ADDITIONAL_NET_PARAMS component)
        net=NetParams(
            inflows=inflow,
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

    alg_run = 'PPO'
    config = deepcopy(ppo.DEFAULT_CONFIG)
    config['num_workers'] = N_CPUS
    config['train_batch_size'] = HORIZON * N_ROLLOUTS
    config['gamma'] = 0.999  # discount rate
    config['model'].update({'fcnet_hiddens': [64, 64]})
    config['clip_actions'] = False
    config['horizon'] = HORIZON
    config['simple_optimizer'] = True

    if args.centralized_vf:
        config['use_centralized_vf'] = True

    # Grid search things
    if args.grid_search:
        config['lr'] = tune.grid_search([5e-4, 5e-5])
        config['num_sgd_iter'] = tune.grid_search([10, 30])
        if args.centralized_vf:
            config['use_centralized_vf'] = tune.grid_search([True, False])

    # LSTM Things
    if args.use_lstm:
        config['model']['use_lstm'] = True
        if args.grid_search:
            config['model']["max_seq_len"] = tune.grid_search([5, 10])
        config['model']["lstm_cell_size"] = 256

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
    return alg_run, env_name, config, flow_params


def on_episode_end(info):
    print(info.keys())
    if 'env' in info:
        env = info['env'].get_unwrapped()[0]
        total_outflow = env.k.vehicle.get_outflow_rate(500)
        inflow = env.inflow
        # round it to 100
        inflow = int(inflow / 100) * 100
        episode = info["episode"]
        episode.custom_metrics["net_outflow_{}".format(inflow)] = total_outflow


def on_train_result(info):
    trainer = info["trainer"]

    trainer.workers.foreach_worker(
        lambda ev: ev.foreach_env(
            lambda env: env.increase_curr_iter()))


if __name__ == '__main__':
    parser = get_multiagent_bottleneck_parser()
    args = parser.parse_args()
    alg_run, env_name, config, flow_params = setup_exps(args)
    config["callbacks"] = {
        "on_episode_end": tune.function(on_episode_end)
    }
    if args.curriculum:
        config["callbacks"].update({"on_train_result": tune.function(on_train_result)})
    if args.multi_node:
        ray.init(redis_address='localhost:6379')
    else:
        ray.init(num_cpus=args.num_cpus + 1)
    eastern = pytz.timezone('US/Eastern')
    date = datetime.now(tz=pytz.utc)
    date = date.astimezone(pytz.timezone('US/Pacific')).strftime("%m-%d-%Y")
    s3_string = "s3://eugene.experiments/old_bottleneck_test/" \
                + date + '/' + args.exp_title
    if args.use_s3:
        run_experiments({
            args.exp_title: {
                'run': alg_run,
                'env': env_name,
                'checkpoint_freq': args.checkpoint_freq,
                'stop': {
                    'training_iteration': args.num_iters
                },
                'config': config,
                'upload_dir': s3_string,
                'num_samples': args.num_samples,
            },
        })
    else:
        run_experiments({
            args.exp_title: {
                'run': alg_run,
                'env': env_name,
                'checkpoint_freq': args.checkpoint_freq,
                'stop': {
                    'training_iteration': args.num_iters
                },
                'config': config,
                'num_samples': args.num_samples,
            },
        })

        # Now we add code to loop through the results and create scores of the results
    # if args.create_inflow_graph:
    #     output_path = os.path.join(os.path.join(os.path.expanduser('~/bottleneck_results'), date), args.exp_title)
    #     if not os.path.exists(output_path):
    #         try:
    #             os.makedirs(output_path)
    #         except OSError as exc:
    #             if exc.errno != errno.EEXIST:
    #                 raise
    #     for (dirpath, dirnames, filenames) in os.walk(os.path.expanduser("~/ray_results")):
    #         if "checkpoint_{}".format(args.checkpoint_freq) in dirpath and dirpath.split('/')[-3] == args.exp_title:
    #             # grab the experiment name
    #             folder = os.path.dirname(dirpath)
    #             tune_name = folder.split("/")[-1]
    #             checkpoint_path = os.path.dirname(dirpath)
    #
    #             ray.shutdown()
    #             if args.local_mode:
    #                 ray.init(local_mode=True)
    #             else:
    #                 ray.init()
    #
    #             run_bottleneck_results(400, 3500, 100, args.num_test_trials, output_path, args.exp_title,
    #                                    checkpoint_path,
    #                                    gen_emission=False, render_mode='no_render',
    #                                    checkpoint_num=dirpath.split('_')[-1],
    #                                    horizon=args.horizon, end_len=500)
    #
    #             if args.use_s3:
    #                 # visualize_adversaries(config, checkpoint_path, 10, 100, output_path)
    #                 for i in range(4):
    #                     try:
    #                         p1 = subprocess.Popen("aws s3 sync {} {}".format(output_path,
    #                                                                          "s3://eugene.experiments/trb_bottleneck_paper/graphs/{}/{}/{}".format(
    #                                                                              date,
    #                                                                              args.exp_title,
    #                                                                              tune_name)).split(
    #                             ' '))
    #                         p1.wait(50)
    #                     except Exception as e:
    #                         print('This is the error ', e)