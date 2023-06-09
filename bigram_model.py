import torch
import torch.nn as nn
import torch.nn.functional as F

BATCH_SIZE = 64
BLOCK_SIZE = 8
TRAIN_SPLIT = 0.8
EMBEDDING_DIM = 128 # @NOTE unused as of yet
TRAINING_ITERS = 3000
LEARNING_RATE = 1e-2
EVAL_ITERS = 200

device = 'cuda' if torch.cuda.is_available() else 'cpu'

# wget https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt

## Open input data file
with open('input.txt', 'r') as file:
    input_text = file.read()

## Tokenize input text (character-level tokenization)
# @TODO use BPE? (tiktoken?)

chars = sorted(list(set(input_text)))
vocab_size = len(chars)
ctoi = { c: i for i, c in enumerate(chars) }
itoc = { i: c for i, c in enumerate(chars) }

for c in chars:
    assert(itoc[ctoi[c]] == c)

encode = lambda string: [ ctoi[c] for c in string ]
decode = lambda tokens: ''.join([ itoc[t] for t in tokens ])

input_toks = encode(input_text)

# @TODO data will contain high-dim embeddings instead of tokens?

data = torch.tensor(input_toks)

## Train/Val split

train_split_idx = int(TRAIN_SPLIT * len(data))
train_data = data[:train_split_idx]
val_data = data[train_split_idx:]

## Generate training examples

def get_batch(split: str):

    data = train_data if split == 'train' else val_data

    # @NOTE highest possible offset generated by randint is `len(train_data) - BLOCK_SIZE - 1`
    # so last possible training example is
    # x = train_data[len(train_data) - BLOCK_SIZE - 1 : len(train_data) - 1]
    # y = train_data[len(train_data) - BLOCK_SIZE : len(train_data)]
    # (we are within bounds!)
    data_offsets = torch.randint(len(data) - BLOCK_SIZE, (BATCH_SIZE,))

    x = torch.stack([ data[offset:offset+BLOCK_SIZE] for offset in data_offsets ])
    y = torch.stack([ data[offset+1:offset+BLOCK_SIZE+1] for offset in data_offsets ])

    x, y = x.to(device), y.to(device)

    return x, y

@torch.no_grad()
def estimate_loss():
    out = {}
    model.eval()
    for split in ['train', 'val']:
        losses = torch.zeros(EVAL_ITERS)
        for k in range(EVAL_ITERS):
            x, y = get_batch(split)
            logits, loss = model(x, y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    # @NOTE Don't forget to put model back into training mode!
    model.train()
    return out

## Define and instantiate simple bigram model

class BigramLanguageModel(nn.Module):

    def __init__(self):
        super().__init__()
        # @NOTE this is not really an embedding, it is a mapping of every token
        # to logits of the next predicted token
        self.logit_table = nn.Embedding(vocab_size, vocab_size)

    def forward(self, batch_toks, batch_tok_targets=None):
        logits = self.logit_table(batch_toks) # (B, T, C)

        if batch_tok_targets is None:
            loss = None
            return logits, loss

        # prepare logits for use with F.cross_entropy
        B, T, C = logits.shape
        logits = logits.view(B*T, C)
        targets = batch_tok_targets.view(B*T)
        loss = F.cross_entropy(logits, targets)

        return logits, loss

    def generate(self, batch_context_toks, max_new_toks):
        for _ in range(max_new_toks):
            logits, _ = self(batch_context_toks) # (B, T, C)
            # we only care about the last time step (will change when we look at larger context window)
            logits = logits[:, -1, :] # (B, 1, C)
            probs = F.softmax(logits, dim=-1) # (B, C)
            batch_next_toks = torch.multinomial(probs, num_samples=1)
            # add new tokens for prediction
            batch_context_toks = torch.cat((batch_context_toks, batch_next_toks), dim=1) # (B, T+1)
        return batch_context_toks


model = BigramLanguageModel()
model = model.to(device)


## Train the model

optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

for iter in range(TRAINING_ITERS):

    if iter % EVAL_ITERS == 0:
        losses = estimate_loss()
        print(f"Step {iter:4d}: train loss: {losses['train']:.4f}, val loss: {losses['val']:.4f}")
        
    # Set gradients to None
    # @NOTE `set_to_none=True` may decrease memory footprint
    optimizer.zero_grad(set_to_none=True)

    x_batch, y_batch = get_batch('train')

    # Forward pass
    logits, loss = model(x_batch, y_batch)

    # Backward pass
    loss.backward()

    optimizer.step()


## Use our trained model to generate text

context = torch.zeros((1, BLOCK_SIZE), dtype=torch.long, device=device)
print(decode(model.generate(context, max_new_toks=500)[0].tolist()))