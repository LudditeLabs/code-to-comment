"""Binary for training translation models and decoding from them.

Running this program without --decode will download the WMT corpus into
the directory specified as --data_dir and tokenize it in a very basic way,
and then start training a model saving checkpoints to --train_dir.

Running with --decode starts an interactive loop so you can see how
the current checkpoint translates English sentences into French.

See the following papers for more information on neural translation models.
 * http://arxiv.org/abs/1409.3215
 * http://arxiv.org/abs/1409.0473
 * http://arxiv.org/abs/1412.2007
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import os
import random
import argparse
import sys
import time
from subprocess import call
import os.path as op

import numpy as np
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf

import data_utils
import seq2seq_model

from evaluation.meteor.meteor import Meteor

import warnings
import logging

_logger = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s %(module)s:%(lineno)s %(levelname)s %(message)s',
    level=logging.DEBUG,
)

warnings.filterwarnings("ignore", category=DeprecationWarning)

# We use a number of buckets and pad to the closest one for efficiency.
# See seq2seq_model.Seq2SeqModel for details of how they work.
_buckets = [(5, 10), (10, 15), (20, 25), (40, 50)]

FLAGS = None


def read_data(source_path, target_path, max_size=None):
    """Read data from source and target files and put into buckets.

    Args:
      source_path: path to the files with token-ids for the source language.
      target_path: path to the file with token-ids for the target language;
        it must be aligned with the source file: n-th line contains the desired
        output for n-th line from the source_path.
      max_size: maximum number of lines to read, all other will be ignored;
        if 0 or None, data files will be read completely (no limit).

    Returns:
      data_set: a list of length len(_buckets); data_set[n] contains a list of
        (source, target) pairs read from the provided data files that fit
        into the n-th bucket, i.e., such that len(source) < _buckets[n][0] and
        len(target) < _buckets[n][1]; source and target are lists of token-ids.
    """
    data_set = [[] for _ in _buckets]
    with tf.gfile.GFile(source_path, mode="r") as source_file, tf.gfile.GFile(target_path, mode="r") as target_file:
        sources, targets = source_file.readlines(), target_file.readlines()
    if max_size and max_size < len(sources):
        sources = sources[:max_size]
        targets = targets[:max_size]
    for source, target in zip(sources, targets):
        source_ids = list(map(int, source.split()))
        target_ids = list(map(int, target.split()))
        target_ids.append(data_utils.EOS_ID)
        for bucket_id, (source_size, target_size) in enumerate(_buckets):
            if len(source_ids) < source_size and len(target_ids) < target_size:
                data_set[bucket_id].append([source_ids, target_ids])
                break
    return data_set


def create_model(session, forward_only, flags):
    """Create translation model and initialize or load parameters in session."""
    model = seq2seq_model.Seq2SeqModel(
        flags.code_vocab_size,
        flags.en_vocab_size,
        _buckets,
        flags.size,
        flags.num_layers,
        flags.max_gradient_norm,
        flags.batch_size,
        flags.learning_rate,
        flags.learning_rate_decay_factor,
        forward_only=forward_only
    )
    ckpt = tf.train.get_checkpoint_state(flags.out_dir)
    if ckpt and ckpt.model_checkpoint_path:
        _logger.info("Reading model parameters from {:s}".format(ckpt.model_checkpoint_path))
        model.saver.restore(session, ckpt.model_checkpoint_path)
    else:
        _logger.info("Created model with fresh parameters.")
        session.run(tf.global_variables_initializer())
    return model


def train():
    """Train a code->en translation model using WMT data."""
    code_train = FLAGS.train_prefix + FLAGS.src
    comment_train = FLAGS.train_prefix + FLAGS.tgt
    code_val = FLAGS.val_prefix + FLAGS.src
    comment_val = FLAGS.val_prefix + FLAGS.tgt

    logs_path = FLAGS.out_dir
    """
    fnameres = 'results_{}_{}_{}_{}.res'.format(FLAGS.num_layers, FLAGS.num_units, FLAGS.batch_size, FLAGS.code_vocab_size)
    fnameparams = 'results_{}_{}_{}_{}.par'.format(FLAGS.num_layers, FLAGS.num_units, FLAGS.batch_size, FLAGS.code_vocab_size)
    fnameres = op.join(logs_path, fnameres)
    fnameparams = op.join(logs_path, fnameparams)
    with open(fnameparams, 'w') as f:
        f.write(str(FLAGS.__flags))
    """
    summary_writer = None
    with tf.Session() as sess:
        #summary_writer = tf.summary.FileWriter(logs_path, graph=tf.get_default_graph())
        # Create model.
        _logger.info("Creating {:d} layers of {:d} units." % (FLAGS.num_layers, FLAGS.num_units))
        model = create_model(sess, False, FLAGS)

        # Read data into buckets and compute their sizes.
        print ("Reading development and training data (limit: %d)."
               % FLAGS.max_train_data_size)
        dev_set = read_data(code_dev, en_dev)
        train_set = read_data(code_train, en_train, FLAGS.max_train_data_size)
        train_bucket_sizes = [len(train_set[b]) for b in xrange(len(_buckets))]
        train_total_size = float(sum(train_bucket_sizes))

        # A bucket scale is a list of increasing numbers from 0 to 1 that we'll use
        # to select a bucket. Length of [scale[i], scale[i+1]] is proportional to
        # the size if i-th training bucket, as used later.
        train_buckets_scale = [sum(train_bucket_sizes[:i + 1]) / train_total_size
                               for i in xrange(len(train_bucket_sizes))]

        # This is the training loop.
        step_time, loss = 0.0, 0.0
        current_step = 0
        previous_losses = []
        while True:
            # Choose a bucket according to data distribution. We pick a random number
            # in [0, 1] and use the corresponding interval in train_buckets_scale.
            random_number_01 = np.random.random_sample()
            bucket_id = min([i for i in xrange(len(train_buckets_scale))
                             if train_buckets_scale[i] > random_number_01])

            # Get a batch and make a step.
            start_time = time.time()
            encoder_inputs, decoder_inputs, target_weights = model.get_batch(
              train_set, bucket_id)

            _, step_loss, output_logits = model.step(sess, encoder_inputs, decoder_inputs,
                                                     target_weights, bucket_id, False,
                                                     summary_writer, global_step=current_step)
            step_time += (time.time() - start_time) / FLAGS.steps_per_checkpoint
            loss += step_loss / FLAGS.steps_per_checkpoint
            current_step += 1

            # Once in a while, we save checkpoint, print statistics, and run evals.
            if current_step % FLAGS.steps_per_checkpoint == 0:
                # Print statistics for the previous epoch.
                perplexity = math.exp(loss) if loss < 300 else float('inf')
                print ("global step %d learning rate %.4f step-time %.2f perplexity "
                       "%.2f" % (model.global_step.eval(), model.learning_rate.eval(),
                                 step_time, perplexity))
                # Decrease learning rate if no improvement was seen over last 3 times.
                if len(previous_losses) > 2 and loss > max(previous_losses[-3:]):
                    sess.run(model.learning_rate_decay_op)
                previous_losses.append(loss)
                # Save checkpoint and zero timer and loss.
                checkpoint_path = os.path.join(FLAGS.train_dir, "translate.ckpt")
                model.saver.save(sess, checkpoint_path, global_step=model.global_step)
                step_time, loss = 0.0, 0.0
                # Run evals on development set and print their perplexity.
                eval_ppx_avg = 0
                for bucket_id in xrange(len(_buckets)):
                    if len(dev_set[bucket_id]) == 0:
                        print("  eval: empty bucket %d" % (bucket_id))
                        continue
                    encoder_inputs, decoder_inputs, target_weights = model.get_batch(
                        dev_set, bucket_id)

                    _, eval_loss, _ = model.step(sess, encoder_inputs, decoder_inputs,
                                                 target_weights, bucket_id, True,
                                                 summary_writer, global_step=current_step)

                    eval_ppx = math.exp(eval_loss) if eval_loss < 300 else float('inf')
                    eval_ppx_avg = eval_ppx_avg + eval_ppx
                    print("  eval: bucket %d perplexity %.2f" % (bucket_id, eval_ppx))
                eval_ppx_avg = eval_ppx_avg / len(_buckets)
                with open(fnameres, 'a') as f:
                    f.write("%f\n" % perplexity)
                    f.write("%f\n" % eval_ppx_avg)
                sys.stdout.flush()


def add_arguments(parser):
    """Build ArgumentParser."""
    parser.register("type", "bool", lambda v: v.lower() == "true")

    # network
    parser.add_argument("--num_units", type=int, default=512, help="Network size.")
    parser.add_argument("--num_layers", type=int, default=2,
                      help="Network depth.")

    # optimizer
    parser.add_argument("--optimizer", type=str, default="sgd", help="sgd | adam")
    parser.add_argument("--learning_rate", type=float, default=0.5,
                      help="Learning rate. Adam: 0.001 | 0.0001")
    parser.add_argument("--start_decay_step", type=int, default=0,
                      help="When we start to decay")
    parser.add_argument("--decay_steps", type=int, default=10000,
                      help="How frequent we decay")
    parser.add_argument("--decay_factor", type=float, default=0.98,
                      help="How much we decay.")
    parser.add_argument(
      "--num_train_steps", type=int, default=12000, help="Num steps to train.")
    parser.add_argument("--colocate_gradients_with_ops", type="bool", nargs="?",
                      const=True,
                      default=True,
                      help=("Whether try colocating gradients with "
                            "corresponding op"))

    # initializer
    parser.add_argument("--init_op", type=str, default="uniform",
                      help="uniform | glorot_normal | glorot_uniform")
    parser.add_argument("--init_weight", type=float, default=0.1,
                      help=("for uniform init_op, initialize weights "
                           "between [-this, this]."))

    # data
    parser.add_argument("--src", type=str, default=None,
                      help="Source suffix, e.g., en.")
    parser.add_argument("--tgt", type=str, default=None,
                      help="Target suffix, e.g., de.")
    parser.add_argument("--train_prefix", type=str, default=None,
                      help="Train prefix, expect files with src/tgt suffixes.")
    parser.add_argument("--val_prefix", type=str, default=None,
                      help="Validation prefix, expect files with src/tgt suffixes.")
    parser.add_argument("--out_dir", type=str, default=None,
                      help="Store log/model files.")

    # Vocab
    parser.add_argument("--vocab_prefix", type=str, default=None, help="""\
      Vocab prefix, expect files with src/tgt suffixes.If None, extract from
      train files.\
      """)
    parser.add_argument("--sos", type=str, default="<s>",
                      help="Start-of-sentence symbol.")
    parser.add_argument("--eos", type=str, default="</s>",
                      help="End-of-sentence symbol.")
    parser.add_argument("--share_vocab", type="bool", nargs="?", const=True,
                      default=False,
                      help="""\
      Whether to use the source vocab and embeddings for both source and
      target.\
      """)

    # Default settings works well (rarely need to change)
    parser.add_argument("--unit_type", type=str, default="lstm",
                      help="lstm | gru | layer_norm_lstm")
    parser.add_argument("--forget_bias", type=float, default=1.0,
                      help="Forget bias for BasicLSTMCell.")
    parser.add_argument("--dropout", type=float, default=0.2,
                      help="Dropout rate (not keep_prob)")
    parser.add_argument("--max_gradient_norm", type=float, default=5.0,
                      help="Clip gradients to this norm.")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size.")

    parser.add_argument("--steps_per_stats", type=int, default=100,
                      help=("How many training steps to do per stats logging."
                            "Save checkpoint every 10x steps_per_stats"))
    parser.add_argument("--max_train", type=int, default=0,
                      help="Limit on the size of training data (0: no limit).")


def main(unused_argv):
    _logger.info("Model training started")
    _logger.info("Unparsed arguments: {}".format(unused_argv))
    train()
    _logger.info("Finish")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    FLAGS, unparsed = parser.parse_known_args()
    tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
