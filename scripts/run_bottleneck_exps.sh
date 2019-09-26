#!/usr/bin/env bash

# 9/05/19 experiments
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
##    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --rollout_scale_factor 0.5 --horizon 2000" \
##    --start --stop --cluster-name exp1 --tmux
##
##ray exec ray_autoscale.yaml \
##"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_LSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
##    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --rollout_scale_factor 0.5 --horizon 2000" \
##    --start --stop --cluster-name exp2 --tmux
##
##ray exec ray_autoscale.yaml \
##"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
##    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --aggregate_info --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp3 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_LSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --aggregate_info --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp4 --tmux
#
#----------------------------------- Add communication ------------------------------------------------------------------------------------------
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_NLSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --communicate --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp5 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_LSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --communicate --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp6 --tmux

#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_NLSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --aggregate_info --communicate --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp7 --tmux

#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_LSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --aggregate_info --communicate --rollout_scale_factor 0.5 --horizon 2000" \
#    --start --stop --cluster-name exp8 --tmux
####################################################################################################################################################
####################################################################################################################################################

# 9/10/19 experiments
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_CN_PEN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --congest_penalty" \
#    --start --stop --cluster-name exp1 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_AG_NCN_PEN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --aggregate_info --rollout_scale_factor 1.0 --horizon 2000 --congest_penalty" \
#    --start --stop --cluster-name exp3 --tmux

####################################################################################################################################################
####################################################################################################################################################
# 9/15/19 experiments with centralized vf
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py MA_NLC_NCM_NLSTM_NAG_CN_CVF --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --central_vf_size 64" \
#    --start --stop --cluster-name exp1 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py MA_NLC_NCM_NLSTM_AG_NCN_CVF --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --aggregate_info --rollout_scale_factor 1.0 --horizon 2000 --central_vf_size 64" \
#    --start --stop --cluster-name exp3 --tmux

####################################################################################################################################################
####################################################################################################################################################
# 9/19/19 experiments with centralized observations, 1 experiment with a longer timestep, and 1 experiment with a higher range of inflows
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_CN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --central_obs --high_inflow 2000" \
#    --start --stop --cluster-name exp1 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py large_sim_step_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --sim_step 1.0 --high_inflow 2000" \
#    --start --stop --cluster-name exp2 --tmux

#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py large_inflows_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 1400 --high_inflow 2200" \
#    --start --stop --cluster-name exp3 --tmux

####################################################################################################################################################
####################################################################################################################################################
# 9/20/19 experiments with a state space that contains edge position
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_CN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --central_obs --high_inflow 2000" \
#    --start --stop --cluster-name exp1 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --high_inflow 2000" \
#    --start --stop --cluster-name exp2 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py MA_NLC_NCM_NLSTM_NAG_NCN_CVF --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --central_vf_size 64 --high_inflow 2000" \
#    --start --stop --cluster-name exp3 --tmux

####################################################################################################################################################
####################################################################################################################################################
# 9/23/19 experiments with high inflows
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_NCN_high_in --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 1600 --high_inflow 2400" \
#    --start --stop --cluster-name exp2 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_NCN_high_in_PEN --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 1600 --high_inflow 2400 --congest_penalty" \
#    --start --stop --cluster-name exp3 --tmux
#
#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py fixed_inflow --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --congest_penalty" \
#    --start --stop --cluster-name exp4 --tmux

#ray exec ray_autoscale.yaml \
#"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py fixed_inflow_lstm --num_iters 350 --checkpoint_freq 50 \
#    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --congest_penalty --use_lstm" \
#    --start --stop --cluster-name exp5 --tmux

####################################################################################################################################################
####################################################################################################################################################
# 9/25/19 experiments with fixed inflows and CVF and centralized obs and aggregate info

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py high_in_CN_NAGG_NLSTM --num_iters 200 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 \
    --central_obs" \
    --start --stop --cluster-name exp1 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py high_in_CN_NAGG_LSTM --num_iters 200 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 4 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --use_lstm \
    --central_obs" \
    --start --stop --cluster-name exp2 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py high_in_CN_NAGG_NLSTM_CVF --num_iters 200 --checkpoint_freq 50 --central_vf_size 64 \
--num_samples 2 --grid_search --n_cpus 1 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --central_obs" --start --stop --cluster-name exp3 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py high_in_CN_NAGG_LSTM_CVF --num_iters 200 --checkpoint_freq 50 --central_vf_size 64 \
--num_samples 2 --grid_search --n_cpus 4 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --use_lstm --central_obs" --start --stop --cluster-name exp4 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py high_in_CN_AGG_NLSTM --num_iters 200 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --aggregate_info \
    --central_obs" \
    --start --stop --cluster-name exp5 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py high_in_CN_AGG_LSTM --num_iters 200 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 4 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --use_lstm --aggregate_info \
    --central_obs" \
    --start --stop --cluster-name exp6 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py high_in_CN_AGG_NLSTM_CVF --num_iters 200 --checkpoint_freq 50 --central_vf_size 64 \
--num_samples 2 --grid_search --n_cpus 1 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --aggregate_info --central_obs" --start --stop --cluster-name exp7 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py high_in_CN_AGG_LSTM_CVF --num_iters 200 --checkpoint_freq 50 --central_vf_size 64 \
--num_samples 2 --grid_search --n_cpus 4 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --use_lstm --aggregate_info --central_obs" --start --stop --cluster-name exp8 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py high_in_NCN_AGG_NLSTM --num_iters 200 --checkpoint_freq 50 \
--num_samples 2 --grid_search --n_cpus 8 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --aggregate_info" \
--start --stop --cluster-name exp1 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multi_bottleneck_centralized.py high_in_NCN_AGG_NLSTM_CVF --num_iters 200 --checkpoint_freq 50 \
--num_samples 2 --grid_search --n_cpus 2 --use_s3 --rollout_scale_factor 1.0 --horizon 2000 --low_inflow 2300 --high_inflow 2301 --aggregate_info --central_vf_size 64" \
--start --stop --cluster-name exp9 --tmux