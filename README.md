# Baby GPT

A simple GPT implementation. It takes the text in the `input.txt` file and writes more like it to `output.txt`.

Uses single-character tokens for now.

## Usage

Put input text into `input.txt`, e.g.
```
wget https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt
```
Then, run `python gpt.py`. The hyperparameters at the beginning of `gpt.py` were set for GPU training, and must be adjusted down if using a CPU to train.
