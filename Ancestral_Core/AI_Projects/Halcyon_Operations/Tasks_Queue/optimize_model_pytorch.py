import torch
import torch.optim as optim
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

def optimize_model():
    print("Optimizing PyTorch model...")

    # Example simple model
    model = nn.Sequential(
        nn.Linear(10, 50),
        nn.ReLU(),
        nn.Linear(50, 1)
    )

    # Optimizer and loss function
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    loss_function = nn.MSELoss()

    # Example data (replace with actual dataset)
    X = torch.rand(100, 10)  # 100 samples, 10 features
    y = torch.rand(100, 1)   # 100 samples, 1 target
    dataset = TensorDataset(X, y)
    data_loader = DataLoader(dataset, batch_size=32)

    # Training loop
    for epoch in range(5):  # Adjust number of epochs
        for batch_X, batch_y in data_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = loss_function(outputs, batch_y)
            loss.backward()
            optimizer.step()
        
        print(f"Epoch {epoch+1} - Loss: {loss.item()}")

    # Save the optimized model
    torch.save(model.state_dict(), "optimized_model.pth")
    print("Model saved as 'optimized_model.pth'.")

if __name__ == "__main__":
    optimize_model()
