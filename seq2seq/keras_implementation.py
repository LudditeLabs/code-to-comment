import data_utils
import numpy as np

from keras.models import Sequential
from keras.layers import Embedding, LSTM, Dense

_buckets = [(5, 10), (10, 15), (20, 25), (40, 50), (250, 100)]


def get_batch(data, bucket_id, batch_size=64):
    """Get a random batch of data from the specified bucket, prepare for step.

    To feed data in step(..) it must be a list of batch-major vectors, while
    data here contains single length-major cases. So the main logic of this
    function is to re-index data cases to be in the proper format for feeding.

    Args:
      data: a tuple of size len(self.buckets) in which each element contains
        lists of pairs of input and output data that we use to create a batch.
      bucket_id: integer, which bucket to get the batch for.

    Returns:
      The triple (encoder_inputs, decoder_inputs, target_weights) for
      the constructed batch that has the proper format to call step(...) later.
    """

    enc_size, dec_size = _buckets[bucket_id]
    enc_inputs, dec_inputs = [], []

    def pad_sequence(iseq, olen, enc=False):
        if enc:
            return list(reversed(iseq + [data_utils.PAD_ID] * (olen - len(iseq))))
        return [data_utils.GO_ID] + iseq + [data_utils.PAD_ID] * (olen - len(iseq) - 1)

    # Get a random batch of encoder and decoder inputs from data,
    # pad them if needed, reverse encoder inputs and add GO to decoder.
    np_data = np.array(data[bucket_id])
    idxs = np.random.choice(np_data.shape[0], size=batch_size, replace=False)
    data = np_data[idxs, :]
    enc_inputs = np.array([pad_sequence(x, enc_size, enc=True) for x in data[:, 0]])
    dec_inputs = np.array([pad_sequence(x, dec_size) for x in data[:, 1]])
    enc_inputs = enc_inputs.swapaxes(0, 1)
    dec_inputs = dec_inputs.swapaxes(0, 1)
    weights = np.ones(dec_inputs.shape)
    idxs = dec_inputs == data_utils.PAD_ID
    weights[:-1, :][idxs[:-1, :]] = 0

    return enc_inputs.swapaxes(0, 1), dec_inputs.swapaxes(0, 1), weights.swapaxes(0, 1)


def build_model(voci_size, voco_size, emb_size, bucket_id):
    model = Sequential()
    model.add(Embedding(voci_size, emb_size, input_length=_buckets[bucket_id][0]))
    model.add(LSTM(emb_size, return_sequences=True))
    model.add(LSTM(emb_size, return_sequences=True))
    model.add(LSTM(emb_size))
    model.add(Dense(voco_size, activation='softmax'))
    return model
    