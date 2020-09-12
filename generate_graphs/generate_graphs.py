import os
import os.path
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
from collections import defaultdict
from cycler import cycler

# https://gist.github.com/thriveth/8560036
CB_color_cycle = ['#377eb8', '#ff7f00', '#4daf4a',
                  '#f781bf', '#a65628', '#984ea3',
                  '#999999', '#e41a1c', '#dede00']
mpl.rcParams['axes.prop_cycle'] = cycler(color=CB_color_cycle)

mpl.rc('font', size=10)  # controls default text sizes
mpl.rc('axes', titlesize=15)  # fontsize of the axes title
mpl.rc('axes', labelsize=15)  # fontsize of the x and y labels
mpl.rc('xtick', labelsize=13)  # fontsize of the tick labels
mpl.rc('ytick', labelsize=13)  # fontsize of the tick labels
mpl.rc('legend', fontsize=13)  # legend fontsize
mpl.rc('figure', titlesize=20)  # fontsize of the figure title


class Data(object):
    def __init__(self, filename, label=None):
        self.filename = filename

        if label is None:
            self.type = 'simple no agg' if 'dqzj2' in filename or 'simplenoagg' in filename \
                else 'simple agg' if 'pos09' in filename or 'simpleagg' in filename \
                else 'complex agg' if 'o9di2' in filename or 'complexagg' in filename \
                else None

            self.penetration = 0.05 if '0p05' in filename \
                        else 0.1 if '0p1' in filename \
                        else 0.2 if '0p2' in filename \
                        else 0.4 if '0p4' in filename \
                        else -1 if 'randompen' in filename \
                        else None

            self.eval_penetration = 0.05 if '0.05' in filename \
                            else 0.1 if '0.1' in filename \
                            else 0.2 if '0.2' in filename \
                            else 0.4 if '0.4' in filename \
                            else None

            assert(None not in [self.type, self.penetration, self.eval_penetration])

            self.transferred = self.penetration != self.eval_penetration
            self.random_pen = self.penetration == -1

            self.label = f'{self.type} '
            self.label += f'{int(self.penetration * 100)}%' if not self.random_pen else 'random pen'
            if self.penetration != self.eval_penetration:
                self.label = f'{self.label} (eval at {int(self.eval_penetration * 100)} %)'

            self.pretty_label = f'{self.type}'.replace('simple no agg', 'minimal').replace('simple agg', 'minimal + aggregate').replace('complex agg', 'radar + aggregate')
            if self.penetration >= 0:
                self.pretty_label += f', {int(self.penetration * 100)}% penetration'
                if self.penetration != self.eval_penetration:
                    self.pretty_label += f' (evaluated at {int(self.eval_penetration * 100)}% penetration)'
            else:
                self.pretty_label += f', evaluated at {int(self.eval_penetration * 100)}% penetration'

            self.label_type, self.label_penetration = self.pretty_label.split(',')
            self.label_eval_penetration = f'evaluated at {int(self.eval_penetration * 100)}% penetration'
        else:
            self.label = label
            self.pretty_label = self.label
            self.label_type = self.label
            self.label_penetration = self.label

        self.load_data()

    def load_data(self):
        """Load data from a bottleneck_outflow file generated by bottleneck_results.py."""
        try:
            outflow_arr = np.loadtxt(self.filename, delimiter=', ')
        except ValueError:
            outflow_arr = np.loadtxt(self.filename, delimiter=',')

        unique_inflows = sorted(list(set(outflow_arr[:, 0])))
        inflows = outflow_arr[:, 0]
        outflows = outflow_arr[:, 1]

        sorted_outflows = {inflow: [] for inflow in unique_inflows}
        for inflow, outflow in zip(inflows, outflows):
            sorted_outflows[inflow].append(outflow)

        mean_outflows = np.asarray([np.mean(sorted_outflows[inflow]) for inflow in unique_inflows])
        std_outflows = np.asarray([np.std(sorted_outflows[inflow]) for inflow in unique_inflows])

        self.unique_inflows = unique_inflows
        self.mean_outflows = mean_outflows
        self.std_outflows = std_outflows


def init_plt_figure(ylabel, xlabel):
    plt.figure(figsize=(10, 6))
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.minorticks_on()
    plt.grid()

def save_plt_figure(title, filename, save_dir='fig', legend_loc='lower left'):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    filename = filename.replace('.', 'p')
    print('Generated', filename)
    plt.legend(loc=legend_loc)
    plt.title(title.replace('simple no agg', 'Minimal').replace('simple agg', 'Minimal + Aggregate').replace('complex agg', 'Radar + Aggregate'))
    plt.savefig(fname=os.path.join(save_dir, filename))

def generate_outflow_inflow_graphs(data_rl, data_baseline):
    """Outflow as a function of inflow."""
    def plot_outflow_inflow(data, label_type, std=True):
        if isinstance(data, list):
            for d in data:
                plot_outflow_inflow(d, label_type, std)
            return
        if label_type == 'type':
            label = data.label_type
        if label_type == 'penetration':
            label = data.label_penetration
        if label_type == 'eval_penetration':
            label = data.label_eval_penetration
        plt.plot(data.unique_inflows, data.mean_outflows, linewidth=2, label=label) #, color='orange')
        if std:
            plt.fill_between(data.unique_inflows, data.mean_outflows - data.std_outflows,
                             data.mean_outflows + data.std_outflows, alpha=0.25) #, color='orange')

    # baseline
    init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Inflow' + r'$ \ \frac{vehs}{hour}$')
    for data in data_baseline:
        if data.label == 'human':
            plot_outflow_inflow(data, 'type')
    save_plt_figure('Inflow vs. Outflow Baseline',
        f'outflow_inflow_baseline', save_dir='figs/outflow_inflow_all', legend_loc='lower right')

    # outflow as a function of inflow (by penetration)
    for penetration in [0.05, 0.1, 0.2, 0.4]:
        for eval_penetration in [0.05, 0.1, 0.2, 0.4]:
            init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Inflow' + r'$ \ \frac{vehs}{hour}$')
            for data in data_rl:
                if data.penetration == penetration and data.eval_penetration == eval_penetration and "RD" not in data.filename:
                    plot_outflow_inflow(data, 'type')
            plot_outflow_inflow(data_baseline, 'type')
            title = f'Inflow vs. Outflow at {int(eval_penetration * 100)}% Penetration (Trained at {int(penetration * 100)}%)' \
                if penetration != eval_penetration \
                else f'Inflow vs. Outflow at {int(penetration * 100)}% Penetration'
            save_plt_figure(title,
                f'outflow_inflow_{penetration}_eval_{eval_penetration}', save_dir='figs/outflow_inflow_all', legend_loc='lower right')

    # inflow vs outflow transfers (0p1 eval all simple agg)
    for penetration in [0.1]:
        for state_type in ['simple no agg', 'simple agg', 'complex agg']:
            init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Inflow' + r'$ \ \frac{vehs}{hour}$')
            for eval_penetration in [0.05, 0.1, 0.2, 0.4]:
                for data in data_rl:
                    if data.penetration == penetration and data.eval_penetration == eval_penetration and data.type == state_type and "RD" not in data.filename:
                        plot_outflow_inflow(data, 'eval_penetration')
            # plot_outflow_inflow(data_baseline, 'type')
            title = f'Inflow vs. Outflow Transfer'
            save_plt_figure(title,
                f'outflow_inflow_{penetration}_eval_all_{state_type.replace(" ", "_")}', save_dir='figs/outflow_inflow_all', legend_loc='lower right')
                

    # outflow as a function of inflow (by state type)
    for state_type in ['simple no agg', 'simple agg', 'complex agg']:
        init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Inflow' + r'$ \ \frac{vehs}{hour}$')
        for data in data_rl:
            if data.type == state_type and not data.transferred and "RD" not in data.filename:
                plot_outflow_inflow(data, 'penetration')
        plot_outflow_inflow(data_baseline, 'penetration')
        save_plt_figure(f'Inflow vs. Outflow for {state_type} State Space',
            f'outflow_inflow_{state_type.replace(" ", "_")}', save_dir='figs/outflow_inflow_no_transfer', legend_loc='lower right')

    # outflow as a function of inflow (by penetration) for training on random penetration
    for state_type in ['simple no agg', 'simple agg', 'complex agg']:
        for additional in ['_lstm_', '_nolstm_']:
            init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Inflow' + r'$ \ \frac{vehs}{hour}$')
            for eval_penetration in [0.05, 0.1, 0.2, 0.4]:
                for data in data_rl:
                    if additional in data.filename and data.type == state_type and data.random_pen and data.eval_penetration == eval_penetration and "RD" not in data.filename:
                        plot_outflow_inflow(data, 'penetration')
            plot_outflow_inflow(data_baseline, 'penetration')
            save_plt_figure('Inflow vs. Outflow for Universal Controller',
                f'outflow_inflow_random_pen{additional}{state_type.replace(" ", "_")}', save_dir='figs/outflow_inflow_random', legend_loc='lower right')


def generate_outflow2400_penetration_graphs(data_rl, data_baseline):
    """Outflow at 2400 inflow as a function of penetration."""
    for state_type in ['simple no agg', 'simple agg', 'complex agg']:
        init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Penetration' + r'$ \ \%$')
        all_data = []
        for data in data_rl:
            if data.type == state_type and not data.transferred and "RD" not in data.filename:
                all_data.append(data)
        assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
        mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
        std_outflows = np.array([d.std_outflows[20] for d in all_data])
        penetrations = np.array([100 * d.penetration for d in all_data], dtype=np.int)
        idx = np.argsort(penetrations)

        pretty_state = state_type.replace('simple no agg', 'minimal').replace('simple agg', 'minimal + aggregate').replace('complex agg', 'radar + aggregate')
        plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=pretty_state) #, color='orange')
        plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
                         mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

        save_plt_figure(f'Penetration vs. Outflow at 2400 Inflow for {state_type} State Space',
            f'outflow2400_penetration_{state_type.replace(" ", "_")}', save_dir='figs/outflow2400_penetration',
            legend_loc='lower right')

    # merge all 3 graphs into 1
    init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Penetration' + r'$ \ \%$')
    for state_type in ['simple no agg', 'simple agg', 'complex agg']:
        all_data = []
        for data in data_rl:
            if data.type == state_type and not data.transferred and "RD" not in data.filename:
                all_data.append(data)
        assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
        mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
        std_outflows = np.array([d.std_outflows[20] for d in all_data])
        penetrations = np.array([100 * d.penetration for d in all_data], dtype=np.int)
        idx = np.argsort(penetrations)

        pretty_state = state_type.replace('simple no agg', 'minimal').replace('simple agg', 'minimal + aggregate').replace('complex agg', 'radar + aggregate')
        plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=pretty_state) #, color='orange')
        plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
                         mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

    save_plt_figure('Penetration vs. Outflow at 2400 Inflow',
        f'outflow2400_penetration_all', save_dir='figs/outflow2400_penetration',
        legend_loc='lower right')

    # get comparison of controller trained at random penetration with the ones trained at fixed penetration
    init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Penetration' + r'$ \ \%$')

    # best universal controllers:
    # simple no agg: nolstm, not cp2000
    # simple agg: nolstm, not cp2000
    # complex agg: nolstm, cp2000

    for i, state_type in enumerate(['simple no agg', 'simple agg', 'complex agg']):
        pretty_state = state_type.replace('simple no agg', 'minimal').replace('simple agg', 'minimal + aggregate').replace('complex agg', 'radar + aggregate')
        color = ['#377eb8', '#ff7f00', '#4daf4a'][i]
        # first universal controller
        all_data = []
        for data in data_rl:
            if data.type == state_type and data.penetration == -1 and "RD" not in data.filename:
                all_data.append(data)
        assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
        mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
        std_outflows = np.array([d.std_outflows[20] for d in all_data])
        penetrations = np.array([100 * d.eval_penetration for d in all_data], dtype=np.int)
        idx = np.argsort(penetrations)
        plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=f'{pretty_state} (universal)', color=color, linestyle='--')
        # plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
        #                     mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

        # then concatenate the ones trained at random penetration
        all_data = []
        for data in data_rl:
            if data.type == state_type and data.penetration == data.eval_penetration and "RD" not in data.filename:
                all_data.append(data)
        assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
        mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
        std_outflows = np.array([d.std_outflows[20] for d in all_data])
        penetrations = np.array([100 * d.eval_penetration for d in all_data], dtype=np.int)
        idx = np.argsort(penetrations)
        plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=f'{pretty_state} (independent)', color=color)
        # plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
        #                     mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

    save_plt_figure(f'Penetration vs. Outflow at 2400 Inflow',
        f'outflow2400_penetration_universal', save_dir='figs/outflow_inflow_random',
        legend_loc='lower right')

    ## reduced radar env (evaluated with 20meters cap)
    init_plt_figure('Outflow' + r'$ \ \frac{vehs}{hour}$', 'Penetration' + r'$ \ \%$')

    all_data = []
    for data in data_rl:
        if data.type == 'complex agg' and "RD_reduced_radar" in data.filename:
            all_data.append(data)
    assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
    mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
    std_outflows = np.array([d.std_outflows[20] for d in all_data])
    penetrations = np.array([100 * d.eval_penetration for d in all_data], dtype=np.int)
    idx = np.argsort(penetrations)
    plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=f'20m radar', color='#377eb8', linestyle='--')
    # plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
    #                     mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

    # then concatenate the ones trained at random penetration
    all_data = []
    for data in data_rl:
        if data.type == 'complex agg' and data.penetration == data.eval_penetration and "RD" not in data.filename:
            all_data.append(data)
    assert(list(set([d.unique_inflows[20] for d in all_data]))[0] == 2400.0)
    mean_outflows = np.array([d.mean_outflows[20] for d in all_data])
    std_outflows = np.array([d.std_outflows[20] for d in all_data])
    penetrations = np.array([100 * d.eval_penetration for d in all_data], dtype=np.int)
    idx = np.argsort(penetrations)
    plt.plot(penetrations[idx], mean_outflows[idx], linewidth=2, label=f'radar', color='#377eb8')
    # plt.fill_between(penetrations[idx], mean_outflows[idx] - std_outflows[idx],
    #                     mean_outflows[idx] + std_outflows[idx], alpha=0.25) #, color='orange')

    save_plt_figure(f'Penetration vs. Outflow at 2400 Inflow for Reduced Radar',
        f'outflow2400_reduced_radar', save_dir='figs/misc/',
        legend_loc='lower right')




def get_outflows_at_3500_inflow(data_rl):
    """Print outflows at 3500 inflow as a function of penetration and state space."""
    data_print = defaultdict(dict)

    for state_type in ['simple no agg', 'simple agg', 'complex agg']:
        all_data = []
        for data in data_rl:
            if data.type == state_type and not data.transferred and "RD" not in data.filename:
                all_data.append(data)
        assert(list(set([d.unique_inflows[31] for d in all_data]))[0] == 3500.0)
        mean_outflows = np.array([d.mean_outflows[31] for d in all_data])
        std_outflows = np.array([d.std_outflows[31] for d in all_data])
        penetrations = np.array([100 * d.penetration for d in all_data], dtype=np.int)

        print(f'\nState space: {state_type}')
        for i in np.argsort(penetrations):
            print(f'\tpenetration={penetrations[i]}%; outflow(3500)={mean_outflows[i]}; std_outflow(3500)={std_outflows[i]}')
            data_print[state_type][penetrations[i]] = (mean_outflows[i], std_outflows[i])
    
    if True:
        # print in latex table syntax
        for penetration in [5, 10, 20, 40]:
            print(fr'{penetration}\%', end=' ')
            for state_type in ['simple no agg', 'simple agg', 'complex agg']:
                mean_outflow, std_outflow = data_print[state_type][penetration]
                print(f'& {int(mean_outflow)} ({int(std_outflow)})', end=' ')
            print(r'\\ \hline')


if __name__ == '__main__':
    generate_plots = False

    # load data
    data_rl = []
    for (dirpath, dirnames, filenames) in os.walk('./data'):
        for filename in filenames:
            if filename.startswith('bottleneck_outflow'):
                data_rl.append(Data(filename=os.path.join(dirpath, filename)))
    type_order = {'simple no agg': 0, 'simple agg': 1, 'complex agg': 2}
    data_rl.sort(key=lambda x: [x.penetration, x.eval_penetration, type_order[x.type], x.label])
        
    data_baseline = []
    data_baseline.append(Data(filename='data/alinea_vs_controller/alinea.csv', label='ALINEA'))
    data_baseline.append(Data(filename='data/alinea_vs_controller/human.csv', label='human'))
    data_baseline.append(Data(filename='data/alinea_vs_controller/p40.csv', label='40% feedback controller'))

    print('Data loaded:', [d.label for d in data_rl + data_baseline])
    print(f'{len(data_rl)} RL data + {len(data_baseline)} baseline data')

    # generate graphs
    # generate_outflow_inflow_graphs(data_rl, data_baseline)
    generate_outflow2400_penetration_graphs(data_rl, data_baseline)

    # print stuff
    # get_outflows_at_3500_inflow(data_rl)
