import torch

from pytorch.chargen.train import inputTensor, categoryTensor
from pytorch.chargen.init import n_letters, all_letters


# Sample from a category and starting letter
def sample(rnn, category, start_letter='A', max_length=20):
    with torch.no_grad():  # no need to track history in sampling
        category_tensor = categoryTensor(category)
        input = inputTensor(start_letter)
        hidden = rnn.initHidden()

        output_name = start_letter

        for i in range(max_length):
            output, hidden = rnn(category_tensor, input[0], hidden)
            topv, topi = output.topk(1)
            topi = topi[0][0]
            if topi == n_letters - 1:
                break
            else:
                letter = all_letters[topi]
                output_name += letter
            input = inputTensor(letter)

        return output_name


# Get multiple samples from one category and multiple starting letters
def samples(rnn, category, start_letters='ABC'):
    for start_letter in start_letters:
        print(sample(rnn, category, start_letter))
