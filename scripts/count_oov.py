"""
Determine words in quora train and test set that are OOV (out of vocabulary)
with respect to the skipthoughts model
"""

import argparse
import os

from collections import defaultdict
import cPickle as pkl

import data_utils as du

import kiros.skipthoughts as st

class FileWriterStdoutPrinter:

    def __init__(self, file_path):
        self.path = file_path

    def __enter__(self):
        self.fd = open(self.path, 'w')

    def __exit__(self, exc_type, exc_value, traceback):
        self.fd.close()

    def emit(self, text):
        print text
        self.fd.write(text)

    def emit_line(self, text):
        print text
        self.fd.write(text + '\n')

def return_0():
    return 0

def analyze_oov(word_dict, quora_data, writer, output_dir, prefix):
    oov_word_freqs = defaultdict(return_0)
    oov_counts_per_question = defaultdict(return_0)
    num_tokens = 0

    for col_label in ['question1', 'question2']:
        print "  ...now handling " + col_label + "..."
        raw_text = st.preprocess(quora_data[col_label])
        for i, q in enumerate(raw_text):
            num_oovs_in_cur_q = 0
            tokens = q.split()
            num_tokens += len(tokens)
            for w in tokens:
                if not w in word_dict:
                    # Count the occurrence of this OOV word
                    oov_word_freqs[w] += 1
                    # Count the occurrence of an OOV word for this question
                    num_oovs_in_cur_q += 1

                    # Signal that the word is OOV with our special signal, which we checked
                    # beforehand is not in train.csv or test.csv
                    orig_text = quora_data[col_label][i]
                    quora_data.set_value(i, col_label, orig_text.replace(w, '%<'+w+'>%'))

            # Increment the histogram count for questions with this number of OOVs
            oov_counts_per_question[num_oovs_in_cur_q] += 1

    # Write everything to disk
    oov_word_fd = open(os.path.join(output_dir, prefix + '_oov_word_freqs.pkl'), 'w')
    pkl.dump(oov_word_freqs, oov_word_fd)
    oov_word_fd.close()

    counts_per_q_fd = open(os.path.join(output_dir, prefix + '_oov_per_q.pkl'), 'w')
    pkl.dump(oov_counts_per_question, counts_per_q_fd)
    counts_per_q_fd.close()

    edited_df_file = os.path.join(output_dir, prefix + '_oov_annot.csv')
    du.write_csv(quora_data, edited_df_file)

    # Some summary stats to humor the user
    writer.emit_line("Num oov words={0} (out of {1}, or {2:.4f}%)".format(len(oov_word_freqs), num_tokens, len(oov_word_freqs)/float(num_tokens)*100))
    writer.emit_line("Num of q's containing oov words={0} (out of {1}, or {2:.4f}%)".format(len(oov_counts_per_question), len(quora_data)*2, float(len(oov_counts_per_question))/len(quora_data)*2*100))

def analyze_dict(word_dict, writer):
    writer.emit_line('Word_dict contains {0} unique entries'.format(len(word_dict)))

def main():
    parser = argparse.ArgumentParser(description='Evaluate a model on the quora question-pair dataset.')
    parser.add_argument('--quora-data-dir', required=True, help='path to the directory containing the quora data')
    parser.add_argument('--st-model-dir', required=True, help='path to the directory containing the skipthoughts model')
    parser.add_argument('--output-dir', default='.', help='path to the directory to write to')
    parser.add_argument('--prefix', default='st_kiros', help='a prefix by which to uniquely identify the files produced by this script')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    output_file = os.path.join(args.output_dir, 'word_counts.txt')
    
    with FileWriterStdoutPrinter(output_file) as writer:
        print "Loading skipthoughts model..."
        model = st.load_model(args.st_model_dir)
        print "Initializing skipthoughts word dict..."
        word_dict = st.init_word_dict(model)
        print "Analyzing word dict..."
        analyze_dict(word_dict, writer)

        print "Loading training set..."
        train = du.load_csv(os.path.join(args.quora_data_dir, 'train.csv'))
        writer.emit_line("Analyzing word counts in train.csv...")
        analyze_oov(word_dict, train, writer, args.output_dir, args.prefix)

        # Be sure to write data to disk for train before moving on to test, which is much bigger

        print "Loading test set..."
        test = du.load_csv(os.path.join(args.quora_data_dir, 'test.csv'))
        writer.emit_line("Analyzing word counts in test.csv...")
        analyze_oov(word_dict, test, writer, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
