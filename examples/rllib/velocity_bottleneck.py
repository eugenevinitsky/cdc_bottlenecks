"""Bottleneck example.

Bottleneck in which the actions are specifying a desired velocity
in a segment of space
"""
import argparse
from datetime import datetime
import json
import sys

import numpy as np
import pytz
import ray
from ray import tune
import ray.rllib.agents.a3c as a3c
import ray.rllib.agents.dqn as dqn
import ray.rllib.agents.ppo as ppo
import ray.rllib.agents.sac as sac
from ray.rllib.models import ModelCatalog
from ray.tune import run_experiments
from ray.tune.registry import register_env

from flow.core.params import SumoParams, EnvParams, InitialConfig, NetParams, \
    InFlows, SumoCarFollowingParams, SumoLaneChangeParams
from flow.core.params import TrafficLightParams
from flow.core.params import VehicleParams
from flow.controllers import RLController, ContinuousRouter, \
    SimLaneChangeController
from flow.models.GRU import GRU
from flow.utils.registry import make_create_env
from flow.utils.rllib import FlowParamsEncoder


def setup_rllib_params(args):
    # time horizon of a single rollout
    horizon = args.horizon
    # number of parallel workers
    n_cpus = args.n_cpus
    # number of rollouts per training iteration scaled by how many sets of rollouts per iter we want
    n_rollouts = int(args.n_cpus * args.rollout_scale_factor)
    return {'horizon': horizon, 'n_cpus': n_cpus, 'n_rollouts': n_rollouts}


def setup_flow_params(args):
    DISABLE_TB = True
    DISABLE_RAMP_METER = True
    AV_FRAC = args.av_frac
    if args.lc_on:
        lc_mode = 1621
    else:
        lc_mode = 512

    vehicles = VehicleParams()
    if not np.isclose(AV_FRAC, 1):
        vehicles.add(
            veh_id="human",
            lane_change_controller=(SimLaneChangeController, {}),
            routing_controller=(ContinuousRouter, {}),
            car_following_params=SumoCarFollowingParams(
                speed_mode=31,
            ),
            lane_change_params=SumoLaneChangeParams(
                lane_change_mode=lc_mode,
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
                lane_change_mode=0,
            ),
            num_vehicles=1)

    # flow rate
    flow_rate = 1900 * args.scaling

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
        "life_penalty": args.life_penalty,
        "av_frac": args.av_frac,
        "lc_mode": lc_mode,
        "congest_penalty_start": args.congest_penalty_start,
        "discrete": args.discrete
    }

    # percentage of flow coming out of each lane
    inflow = InFlows()
    if not np.isclose(args.av_frac, 1.0):
        inflow.add(
            veh_type='human',
            edge='1',
            vehs_per_hour=flow_rate * (1 - args.av_frac),
            departLane='random',
            departSpeed=10.0)
        inflow.add(
            veh_type='av',
            edge='1',
            vehs_per_hour=flow_rate * args.av_frac,
            departLane='random',
            departSpeed=10.0)
    else:
        inflow.add(
            veh_type='av',
            edge='1',
            vehs_per_hour=flow_rate,
            departLane='random',
            departSpeed=10.0)

    traffic_lights = TrafficLightParams()
    if not DISABLE_TB:
        traffic_lights.add(node_id='2')
    if not DISABLE_RAMP_METER:
        traffic_lights.add(node_id='3')

    additional_net_params = {'scaling': args.scaling, "speed_limit": 23.0}

    flow_params = dict(
        # name of the experiment
        exp_tag=args.exp_title,

        # name of the flow environment the experiment is running on
        env_name='DesiredVelocityEnv',

        # name of the scenario class the experiment is running on
        scenario='BottleneckScenario',

        # simulator that is used by the experiment
        simulator='traci',

        # sumo-related parameters (see flow.core.params.SumoParams)
        sim=SumoParams(
            sim_step=args.sim_step,
            render=args.render,
            print_warnings=False,
            restart_instance=True,
        ),

        # environment related parameters (see flow.core.params.EnvParams)
        env=EnvParams(
            warmup_steps=int(args.warmup_steps / (args.sims_per_step * args.sim_step)),
            sims_per_step=args.sims_per_step,
            horizon=args.horizon,
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
    return flow_params



def setup_exps(args):
    rllib_params = setup_rllib_params(args)
    flow_params = setup_flow_params(args)
    alg_run = args.algorithm
    if alg_run == 'PPO':
        config = ppo.DEFAULT_CONFIG.copy()
        config['vf_clip_param'] = 100
        config['vf_share_layers'] = True
        config['simple_optimizer'] = False

        if args.grid_search:
            config['num_sgd_iter'] = tune.grid_search([10, 30])
    elif alg_run == 'A3C':
        if args.grid_search:
            config['sample_batch_size'] = tune.grid_search([10, 100])
        config = a3c.DEFAULT_CONFIG.copy()
    elif alg_run == 'DQN':
        if alg_run == 'DQN' and not args.discrete:
            sys.exit("If you are using DQN, make sure to pass in the --discrete flag as well.")
        config = dqn.DEFAULT_CONFIG.copy()
    elif alg_run == 'SAC':
        if args.use_gru or args.use_lstm:
            sys.exit("SAC does not support LSTM or GRU")
        config = sac.DEFAULT_CONFIG.copy()
    else:
        sys.exit("Please specify a valid algorithm amongst A3C, PPO, SAC, or DQN")

    # General config params
    config['num_workers'] = rllib_params['n_cpus']
    config['train_batch_size'] = args.horizon * rllib_params['n_rollouts']
    config['gamma'] = 0.995  # discount rate
    config['clip_actions'] = True
    config['horizon'] = args.horizon

    # Grid search things
    if args.grid_search and (alg_run == 'PPO' or alg_run == 'A3C'):
        config['lr'] = tune.grid_search([5e-5, 5e-4])

    if args.use_lstm and args.use_gru:
        sys.exit("You should not specify both an LSTM and a GRU")
    # Model setup things
    config['model']['use_lstm'] = args.use_lstm
    if args.use_lstm:
        config['model']["max_seq_len"] = tune.grid_search([10, 20])
        config['model'].update({'fcnet_hiddens': []})
        config['model']["lstm_cell_size"] = 64
    else:
        config['model'].update({'fcnet_hiddens': [256, 256]})

    if args.use_gru:
        config['model']["max_seq_len"] = tune.grid_search([10, 20])
        config['model'].update({'fcnet_hiddens': []})
        model_name = "GRU"
        ModelCatalog.register_custom_model(model_name, GRU)
        config['model']['custom_model'] = model_name
        config['model']['custom_options'] = {"cell_size": 64}

    # save the flow params for replay
    flow_json = json.dumps(
        flow_params, cls=FlowParamsEncoder, sort_keys=True, indent=4)
    config['env_config']['flow_params'] = flow_json
    config['env_config']['run'] = alg_run

    create_env, env_name = make_create_env(params=flow_params, version=0)

    # Register as rllib env
    register_env(env_name, create_env)

    return alg_run, env_name, config


def on_episode_end(info):
    env = info['env'].get_unwrapped()[0]
    outflow_over_last_500 = env.k.vehicle.get_outflow_rate(int(500 / env.sim_step))
    inflow = env.inflow
    # round it to 100
    inflow = int(inflow / 100) * 100
    episode = info["episode"]
    episode.custom_metrics["net_outflow_{}".format(inflow)] = outflow_over_last_500


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Parses command line args for single-agent bottleneck exps')

    # required input parameters for tune
    parser.add_argument('exp_title', type=str, help='Informative experiment title to help distinguish results')
    parser.add_argument('--use_s3', action='store_true', help='If true, upload results to s3')
    parser.add_argument('--n_cpus', type=int, default=1, help='Number of cpus to run experiment with')
    parser.add_argument('--multi_node', action='store_true', help='Set to true if this will '
                                                                       'be run in cluster mode')
    parser.add_argument("--num_iters", type=int, default=350)
    parser.add_argument("--checkpoint_freq", type=int, default=50)
    parser.add_argument("--num_samples", type=int, default=1)
    parser.add_argument("--grid_search", action='store_true')
    parser.add_argument("--algorithm", type=str, default='PPO', help='Algorithm of choice. Current supported options are'
                                                                     'PPO and A3C')
    parser.add_argument("--use_gru", action='store_true', help='Whether to use a GRU as the model')

    # arguments for flow
    parser.add_argument('--low_inflow', type=int, default=800, help='the lowest inflow to sample from')
    parser.add_argument('--high_inflow', type=int, default=2000, help='the highest inflow to sample from')
    parser.add_argument('--render', action='store_true', help='Show sumo-gui of results')
    parser.add_argument('--horizon', type=int, default=1000, help='Horizon of the environment')
    parser.add_argument('--warmup_steps', type=int, default=100, help='How many seconds worth of warmup steps to take')
    parser.add_argument('--sim_step', type=float, default=0.5, help='Time step of the simulator')
    parser.add_argument('--sims_per_step', type=int, default=1, help='Time step of the simulator')
    parser.add_argument('--av_frac', type=float, default=0.1, help='What fraction of the vehicles should be autonomous')
    parser.add_argument('--scaling', type=int, default=1, help='How many lane should we start with. Value of 1 -> 4, '
                                                               '2 -> 8, etc.')
    parser.add_argument('--lc_on', action='store_true', help='If true, lane changing is enabled.')
    parser.add_argument('--congest_penalty', action='store_true', help='If true, an additional penalty is added '
                                                                            'for vehicles queueing in the bottleneck')
    parser.add_argument('--life_penalty', type=float, default=3, help='How much to subtract in the reward at each '
                                                                     'time-step for remaining in the system.')
    parser.add_argument('--congest_penalty_start', type=int, default=30, help='If congest_penalty is true, this '
                                                                              'sets the number of vehicles in edge 4'
                                                                              'at which the penalty sets in')
    parser.add_argument('--discrete', action='store_true', help='If true the action space is discrete')

    # arguments for ray
    parser.add_argument('--rollout_scale_factor', type=float, default=1, help='the total number of rollouts is'
                                                                            'args.n_cpus * rollout_scale_factor')
    parser.add_argument('--use_lstm', action='store_true')

    args = parser.parse_args()

    alg_run, env_name, config = setup_exps(args)
    if args.multi_node:
        ray.init(redis_address='localhost:6379')
    else:
        ray.init(num_cpus=args.n_cpus + 1)

    # store custom metrics
    config["callbacks"] = {"on_episode_end": tune.function(on_episode_end)}

    eastern = pytz.timezone('US/Eastern')
    date = datetime.now(tz=pytz.utc)
    date = date.astimezone(pytz.timezone('US/Pacific')).strftime("%m-%d-%Y")
    s3_string = "s3://eugene.experiments/trb_bottleneck_paper/" \
                + date + '/' + args.exp_title

    exp_dict = {
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
    }
    if args.use_s3:
        exp_dict[args.exp_title]['upload_dir'] = s3_string

    run_experiments(exp_dict, queue_trials=True)
