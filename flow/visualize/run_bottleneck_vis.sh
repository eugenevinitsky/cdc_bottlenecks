#!/bin/bash

python bottleneck_results.py /Users/eugenevinitsky/ray_results/test/ImitationPPOTrainer_MultiBottleneckImitationEnv-v0_0_2019-11-23_16-43-051m6qa0ck 50 test \
--num_trials 3 --outflow_min 2600 --outflow_max 2600 --num_cpus 1 --render_mode sumo_gui
