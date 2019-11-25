from ray.rllib.agents.ppo.ppo import PPOTrainer
from ray.rllib.agents.ppo.ppo_policy import PPOTFPolicy
from ray.rllib.agents.ppo.ppo_policy import LearningRateSchedule, EntropyCoeffSchedule, KLCoeffMixin, ValueNetworkMixin
from ray.rllib.utils.annotations import override, DeveloperAPI
from ray.rllib.utils.explained_variance import explained_variance
from ray.rllib.evaluation.postprocessing import Postprocessing
from ray.rllib.policy.policy import Policy
from ray.rllib.models.model import restore_original_dimensions
from ray.rllib.agents.ppo.ppo_policy import ppo_surrogate_loss, kl_and_loss_stats
import tensorflow as tf


def imitation_loss(policy, model, dist_class, train_batch):
    original_space = restore_original_dimensions(train_batch['obs'], model.obs_space)
    expert_tensor = original_space['expert_action']
    logits, state = model.from_batch(train_batch)
    action_dist = dist_class(logits, model)
    policy_actions = action_dist.sample()
    imitation_loss = tf.reduce_mean(tf.squared_difference(policy_actions, expert_tensor))
    return imitation_loss


# def new_ppo_surrogate_loss(policy, batch_tensors):
def new_ppo_surrogate_loss(policy, model, dist_class, train_batch):
    policy.imitation_loss = imitation_loss(policy, model, dist_class, train_batch)
    return policy.policy_weight * ppo_surrogate_loss(policy, model, dist_class, train_batch) \
               + policy.imitation_weight * policy.imitation_loss


@DeveloperAPI
class ImitationLearningRateSchedule(object):
    """Mixin for TFPolicy that adds a learning rate schedule."""

    @DeveloperAPI
    def __init__(self, num_imitation_iters, imitation_weight, config):
        self.imitation_weight = tf.get_variable("imitation_weight", initializer=float(imitation_weight),
                                                trainable=False, dtype=tf.float32)
        self.policy_weight = tf.get_variable("policy_weight", initializer=0.0, trainable=False,
                                             dtype=tf.float32)
        self.start_kl_val = config["kl_coeff"]
        self.num_imitation_iters = num_imitation_iters
        self.curr_iter = 0

    @override(Policy)
    def on_global_var_update(self, global_vars):
        super(ImitationLearningRateSchedule, self).on_global_var_update(global_vars)

        if self.curr_iter > self.num_imitation_iters:
            self.imitation_weight.load(0.0, session=self._sess)
            self.policy_weight.load(1.0, session=self._sess)
        else:
            # we don't want the kl coefficient to go wild while we are imitating
            self.kl_coeff.load(self.start_kl_val, session=self.get_session())
        self.curr_iter += 1


def loss_state(policy, train_batch):
    stats = kl_and_loss_stats(policy, train_batch)
    stats.update({'imitation_loss': policy.imitation_loss, 'policy_weight': policy.policy_weight,
                  'imitation_weight': policy.imitation_weight})
    return stats


def setup_mixins(policy, obs_space, action_space, config):
    ValueNetworkMixin.__init__(policy, obs_space, action_space, config)
    KLCoeffMixin.__init__(policy, config)
    EntropyCoeffSchedule.__init__(policy, config["entropy_coeff"],
                                  config["entropy_coeff_schedule"])
    LearningRateSchedule.__init__(policy, config["lr"], config["lr_schedule"])
    ImitationLearningRateSchedule.__init__(policy, config["model"]["custom_options"]["num_imitation_iters"],
                                           config["model"]["custom_options"]["imitation_weight"], config)



def grad_stats(policy, train_batch, grads):
    return {
        "grad_gnorm": tf.global_norm(grads),
        "vf_explained_var": explained_variance(
            train_batch[Postprocessing.VALUE_TARGETS],
            policy.model.value_function()),
    }


ImitationPolicy = PPOTFPolicy.with_updates(
    name="ImitationPolicy",
    before_loss_init=setup_mixins,
    stats_fn=loss_state,
    grad_stats_fn=grad_stats,
    loss_fn=new_ppo_surrogate_loss,
    mixins=[
        LearningRateSchedule, EntropyCoeffSchedule, KLCoeffMixin,
        ValueNetworkMixin, ImitationLearningRateSchedule
    ])

ImitationTrainer = PPOTrainer.with_updates(name="ImitationPPOTrainer", default_policy=ImitationPolicy)