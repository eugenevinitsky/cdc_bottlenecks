#!/usr/bin/env bash
ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp1 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_LSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp2 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_NLSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --aggregate_info --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp3 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_NCM_LSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --aggregate_info --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp4 --tmux

----------------------------------- Add communication ------------------------------------------------------------------------------------------
ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_NLSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --communicate --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp5 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_LSTM_NAG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --communicate --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp6 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_NLSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_s3 --aggregate_info --communicate --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp7 --tmux

ray exec ray_autoscale.yaml \
"python flow/examples/rllib/multiagent_exps/multiagent_bottleneck.py MA_NLC_CM_LSTM_AG_NCN --num_iters 350 --checkpoint_freq 50 \
    --num_samples 2 --grid_search --n_cpus 30 --use_lstm --use_s3 --aggregate_info --communicate --rollout_scale_factor 1.0 --horizon 2000" \
    --start --stop --cluster-name exp8 --tmux
