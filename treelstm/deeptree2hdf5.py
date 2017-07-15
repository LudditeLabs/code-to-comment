import h5py
import argparse
import re
import pickle
from collections import defaultdict

REGEXP = '([\w_]+)\((.*?)\-([\d]+), (.*?)\-([\d]+)\)'

ROOT_MARK = '###root###'
UNK_TOKEN = '###unk###'


def parse_dep_str(depStr):
    depWords = []
    mats = re.findall(REGEXP, depStr)
    for rel, w1, p1, w2, p2 in mats:
        if w1 == 'ROOT' and p1 == '0':
            w1 = ROOT_MARK
        depWords.append({'rel': rel, 'w1': w1, 'p1': int(p1), 'w2': w2, 'p2': int(p2)})
    return depWords


def dwords_2_words(dwords):
    words = {}
    maxID = -1
    for dword in dwords:
        wid = dword['p2']
        words[wid] = dword['w2']
        maxID = max((wid, maxID))
    words[1] = ROOT_MARK
    return words


def create_vocab(inputFile, freqCut, ignoreCase, keepFreq):
    with open(inputFile) as f:
        lines = f.readlines()
    wordVector = []
    wordFreq = defaultdict(int)
    for l in lines:
        if not l:
            continue
        fields = l.split('\t')
        depWords = parse_dep_str(fields[1])
        words = dwords_2_words(depWords)
        for k, v in words.iteritems():
            if ignoreCase:
                words[k] = v.lower()
            wordFreq[words[k]] += 1
            wordVector = list(set(wordVector + words[k]))
    print('totally {} lines'.format(len(lines)))
    wid = 1
    word2idx = {}
    word2idx[UNK_TOKEN] = wid
    wid = wid + 1
    uniqUNK = 0
    freqs = [0]
    for word in wordVector:
        if wordFreq[word] > freqCut:
            word2idx[word] = wid
            freqs.append(wordFreq[word])
            wid = wid + 1
        else:
            uniqUNK = uniqUNK + 1
            freqs[0] += wordFreq[word]

    vocabSize = wid - 1
    idx2word = {}
    for k, v in word2idx.iteritems():
        idx2word[v] = k

    vocab = {'word2idx': word2idx, 'idx2word': idx2word, 'freqCut': freqCut,
        'ignoreCase': ignoreCase, 'keepFreq': keepFreq, 'UNK': word2idx[UNK_TOKEN],
        'UNK_TOKEN': UNK_TOKEN}

    if keepFreq:
        vocab['freqs'] = freqs
        vocab['uniqUNK'] = uniqUNK
        print('freqs size {}'.format(len(freqs)))

    print('original words count {}, after cut = {}, words count {}'.format(len(wordVector), freqCut, vocabSize))
    vocab['nvocab'] = vocabSize
    return vocab


def deptree_2_hdf5_bidirectional(depFile, h5out, label, vocab, maxLen):
    lineNo = 0
    offset = 1
    delCnt = 0
    loffset = 1
    # TODO: implement later


def deptree_2_hdf5(depFile, h5out, label, vocab, maxLen):
    lineNo = 0
    offset = 1
    delCnt = 0
    gxdata = '/{}/x_data'.format(label)
    gydata = '/{}/y_data'.format(label)
    gindex = '/{}/index'.format(label)
    isFirst = True


def parse_args():
    parser = argparse.ArgumentParser('verwerk')

    parser.add_argument('--train', type=str, default=None, help='train text file')
    parser.add_argument('--valid', type=str, default=None, help='valid text file')
    parser.add_argument('--test', type=str, default=None, help='test text file')
    parser.add_argument('--dataset', type=str, default=None, help='the resulting dataset (.h5)')
    parser.add_argument('--freq', type=int, default=0, help='words less than or equals to "freq" times will be replaced with UNK token')
    parser.add_argument('--ignoreCase', type=bool, default=False, help='case will be ignored')
    parser.add_argument('--keepFreq', type=bool, default=False, help='keep frequency information during creating vocabulary')
    parser.add_argument('--maxLen', type=int, default=100, help='sentences longer than maxlen will be ignored!')
    parser.add_argument('--sort', type=int, default=0, help='0: no sorting of the training data; -1: sort training data by their length; k (k > 0): sort the consecutive k batches by their length')
    parser.add_argument('--batchSize', type=int, default=64, help='batch size when --sort > 0 or --sort == -1')
    parser.add_argument('--bidirectional', type=bool, default=False, help='create bidirectional model')

    args = parser.parse_args()
    return args


def main():
    opts = parse_args()
    print(opts)
    vocab = create_vocab(opts.train, opts.freq, opts.ignoreCase, opts.keepFreq)
    dataPrefix = opts.dataset[:-4]
    vocabPath = dataPrefix + '.vocab.pyt'
    print('save vocab to {}'.format(vocabPath))
    pickle.dump(vocab, open(vocabPath, 'w'))
    h5out = h5py.File(opts.dataset, 'w')
    if opts.bidirectional:
        deptree_2_hdf5_bidirectional(opts.train, h5out, 'train', vocab, opts.maxLen)
    else:
        deptree_2_hdf5(opts.train, h5out, 'train', vocab, opts.maxLen)


if __name__ == '__main__':
    main()
