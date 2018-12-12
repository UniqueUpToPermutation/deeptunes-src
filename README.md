# Deep Tunes

## Examples

Examples of output from our generative model can be heard [here](https://web.stanford.edu/~paetter/deeptunesresults/deeptunesresults.html)

## Requirements

Need to set up two anaconda environments for this project because the different parts require different python versions.

- For training and translating, set up and OpenNMT according to: [OpenNMT-py Installation](http://opennmt.net/OpenNMT-py/main.html#installation).
- For converting text to midi files, set up by following the instructions on [Clara: A Neural Net Music Generator](https://github.com/mcleavey/musical-neural-net)

## Data

We use a subset of the data provided by [Clara: A Neural Net Music Generator](https://github.com/mcleavey/musical-neural-net) at [Notewise piano solo text files](http://www.christinemcleavey.com/files/notewise_piano_solo.tar.gz). This consists of data preprocessed from midi to text format as specified by the text encoding. We only use Bach and Mozart.

## Data Processing Pipeline

- Use ```data/dirn2c.py``` to process the Bach and Mozart directories to generate source and target files for each piece. Each source and target file contains the corresponding snippets for chord and note encoding respectively.
- We then use ```data/make-all-seqs-shuffled-bach-mozart.ipynb``` and ```data/make-train-val-test-data_3.ipynb``` to consolidate the data, shuffle it and generate training (100000 samples), validation (1000 samples), and various test sets. We include a sample test set in ```data/src-text.txt```.

## Training

We use [OpenNMT-py Translation](http://opennmt.net/OpenNMT-py/extended.html) commands to preprocess, train and evaluate. All training and evaluation needs to be done in the OpenNMT env. Our preprocessing and training code for the model we use (determined after a lot of hyper parameter search) is as follows:

- preprocess:

  ```bash
  python OpenNMT-py/preprocess.py \
  	-train_src ./data/data_3/src-train.txt \
  	-train_tgt ./data/data_3/tgt-train.txt \
  	-valid_src ./data/data_3/src-val.txt \
  	-valid_tgt ./data/data_3/tgt-val.txt \
  	-save_data ./data/data_3 \
  	-tgt_seq_length 1000
  ```

- Train:

  ```bash
  python OpenNMT-py/train.py \
  	-src_word_vec_size 300 \
  	-tgt_word_vec_size 300 \
  	-encoder_type brnn \
  	-decoder_type rnn \
  	-enc_layers 4 \
  	-dec_layers 4 \
  	-enc_rnn_size 400 \
  	-dec_rnn_size 400 \
  	-rnn_type LSTM \
  	-data ./data/data_3 \
  	-save_model ./exps/exp_5/r1 \
  	-save_checkpoint_steps 2000 \
  	-gpu_ranks 0 \
  	-world_size 1 \
  	-batch_size 64 \
  	-valid_steps 500 \
  	-train_steps 100000 \
  	-optim sgd \
  	-dropout 0.1 \
  	-learning_rate 0.5 \
  	-learning_rate_decay 0.5 \
  	-start_decay_steps 30000 \
  	-decay_steps 20000 \
  	-report_every 100 \
  	-log_file ./exps/exp_5/log_r1 
  
  python OpenNMT-py/train.py \
  	-src_word_vec_size 300 \
  	-tgt_word_vec_size 300 \
  	-encoder_type brnn \
  	-decoder_type rnn \
  	-enc_layers 4 \
  	-dec_layers 4 \
  	-enc_rnn_size 400 \
  	-dec_rnn_size 400 \
  	-rnn_type LSTM \
  	-data ./data/data_3 \
  	-save_model ./exps/exp_5/r2 \
  	-save_checkpoint_steps 1000 \
  	-reset_optim all \
  	-gpu_ranks 0 \
  	-world_size 1 \
  	-train_from ./exps/exp_5/r1_step_42000.pt \
  	-batch_size 64 \
  	-valid_steps 500 \
  	-train_steps 2000 \
  	-optim sgd \
  	-dropout 0.1 \
  	-learning_rate 0.125 \
  	-learning_rate_decay 0.5 \
  	-start_decay_steps 50000 \
  	-decay_steps 10000 \
  	-report_every 100 \
  	-log_file ./exps/exp_5/log_r2
  ```

- To generate the learning curves, use ```monitor_training.ipynb```.

- We include the pretrained model that we use in ```exps/r2_step_2000.pt```. You can evaluate with this model on the test data we have provided using:

  ```bash
  python OpenNMT-py/translate.py \
  	-model ./exps/r2_step_2000.pt \
  	-src ./data/src-test.txt \
  	-output ./exps/test_r2_step_2000.txt \
  	-max_length 200
  ```

## Converting to midi

To convert the files to midi, activate the env for Clara and then use ```make_midi.ipynb```. Note the code for this was reused from [Clara: A Neural Net Music Generator](https://github.com/mcleavey/musical-neural-net).

