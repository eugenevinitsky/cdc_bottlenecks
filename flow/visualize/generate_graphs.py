import os
import ray
from flow.visualize.bottleneck_results import run_bottleneck_results
import subprocess
import errno
import sys


def aws_sync(src, dest):
    print('AWS S3 SYNC FROM >>> {} <<< TO >>> {} <<<'.format(src, dest))
    for _ in range(4):
        try:
            p1 = subprocess.Popen('aws s3 sync {} {}'.format(src, dest).split(' '))
            p1.wait(3600)
        except Exception as e:
            print('This is the error ', e)


NUM_TEST_TRIALS = 1

OUTFLOW_MIN = 400
OUTFLOW_MAX = 3600
OUTFLOW_STEP = 100

if __name__ == '__main__':
    exp_cp_path = sys.argv[1]
    print("exp cp path: ", exp_cp_path)
    exp_title = exp_cp_path.replace('/', '_')

    # download checkpoints from AWS
    os.makedirs(os.path.expanduser("~/ray_results"))
    aws_sync('s3://nathan.experiments/trb_bottleneck_paper/' + exp_cp_path,
             os.path.expanduser("~/ray_results/trb_bottleneck_paper/" + exp_cp_path))

    ray.init()
    
    output_path = os.path.join(os.path.expanduser('~/bottleneck_results'))
    os.makedirs(output_path)

    run_bottleneck_results(OUTFLOW_MIN, OUTFLOW_MAX, OUTFLOW_STEP, NUM_TEST_TRIALS, output_path, exp_title, exp_cp_path,
                            gen_emission=True, render_mode='no_render', checkpoint_num="2000",
                            horizon=400, end_len=500)  

    aws_sync(output_path,
            os.path.join("s3://nathan.experiments/trb_bottleneck_paper/seeds_graphs/", exp_title))



    # DATE = "07-30-2020"

    # for EXP_TITLE in EXP_TITLE_LIST:
    #     # create output dir
    #     output_path = os.path.join(os.path.expanduser('~/bottleneck_results'), EXP_TITLE)
    #     if not os.path.exists(output_path):
    #         try:
    #             os.makedirs(output_path)
    #         except OSError as exc:
    #             if exc.errno != errno.EEXIST:
    #                 raise

    #     # for each grid search, find checkpoint 2000
    #     for (dirpath, dirnames, filenames) in os.walk(os.path.expanduser("~/ray_results")):
    #         if "checkpoint_2000" in dirpath and EXP_TITLE in dirpath: #dirpath.split('/')[-3] == EXP_TITLE:
    #             print('FOUND CHECKPOINT {}'.format(dirpath))

    #             # grab the experiment name
    #             folder = os.path.dirname(dirpath)
    #             tune_name = folder.split("/")[-1]
    #             checkpoint_path = os.path.dirname(dirpath)

    #             print('GENERATING GRAPHS')
    #             run_bottleneck_results(OUTFLOW_MIN, OUTFLOW_MAX, OUTFLOW_STEP, NUM_TEST_TRIALS, output_path, EXP_TITLE.replace('/', '_'), checkpoint_path,
    #                                     gen_emission=False, render_mode='no_render', checkpoint_num="2000",
    #                                     horizon=400, end_len=500)

    #             aws_sync(output_path,
    #                     "s3://nathan.experiments/trb_bottleneck_paper/seed_graphs/{}/{}/{}".format(DATE, EXP_TITLE.replace('/', '_'), tune_name))
