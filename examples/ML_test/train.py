# train.py
import torch
import torch.optim as optim
from torchvision import datasets, transforms
from model import SimpleCNN

BATCH_SIZE = 64
EPOCHS = 1
LR = 0.01

def main():
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])

    trainset = datasets.CIFAR10(
        root="data/cifar10",
        train=True,
        download=False,
        transform=transform
    )

    trainloader = torch.utils.data.DataLoader(
        trainset,
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    model = SimpleCNN()
    optimizer = optim.SGD(model.parameters(), lr=LR)
    criterion = torch.nn.CrossEntropyLoss()

    model.train()
    for epoch in range(EPOCHS):
        for images, labels in trainloader:
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

    torch.save(model.state_dict(), "model.pt")
    print("Training complete. Model saved to model.pt")

if __name__ == "__main__":
    main()

