# CNN + Transformer 时间序列模型：与参考实现（more-than-moore/scripts/ml/
# cnn-transformer-forecast）逐层等价的移植。结构、默认超参、初始化顺序均保持
# 一致，以保证同 seed 下数值可复现；修改任何一层都会破坏与参考指标的比对。
from __future__ import annotations

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset


class TimeSeriesDataset(Dataset):
    def __init__(self, X: torch.Tensor, y: torch.Tensor):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class CNNTransformer(nn.Module):
    """CNN 提局部模式，Transformer 建模全局依赖，取末时间步回归。"""

    def __init__(
        self,
        input_dim: int = 1,
        cnn_channels: int = 32,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv1d(input_dim, cnn_channels, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(cnn_channels, cnn_channels, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.project = nn.Linear(cnn_channels, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.permute(0, 2, 1)
        x = self.cnn(x)
        x = x.permute(0, 2, 1)
        x = self.project(x)
        x = self.transformer(x)
        x = x[:, -1, :]
        return self.head(x)


class MultiCNNTransformer(CNNTransformer):
    """多变量输出版：骨干与单变量完全一致，仅回归头改为 N 通道输出。"""

    def __init__(self, input_dim: int, output_dim: int, **kwargs):
        super().__init__(input_dim=input_dim, **kwargs)
        self.head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim),
        )


def make_loader(
    X, y, batch_size: int, shuffle: bool
) -> DataLoader:
    return DataLoader(
        TimeSeriesDataset(X, y), batch_size=batch_size, shuffle=shuffle
    )
