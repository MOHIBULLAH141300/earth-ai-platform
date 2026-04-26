"""
EarthAI Platform - ML/DL Training Pipeline
Implements CNN, LSTM, Transformer, and ensemble models for Earth system modeling
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, TensorDataset
from torch.optim import Adam, AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau, CosineAnnealingLR
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
import logging
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
try:
    import wandb
except ImportError:  # Optional dependency in core runtime
    wandb = None

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for model training"""
    model_type: str
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    early_stopping_patience: int = 10
    validation_split: float = 0.2
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    mixed_precision: bool = True
    gradient_clip: float = 1.0
    
    # Model-specific
    num_classes: int = 2
    input_channels: int = 12  # For multi-spectral imagery
    sequence_length: int = 30  # For time series
    hidden_dim: int = 256
    num_layers: int = 4
    dropout: float = 0.2
    
    # Transformer-specific
    num_heads: int = 8
    dim_feedforward: int = 1024
    
    # CNN-specific
    num_filters: List[int] = None
    kernel_sizes: List[int] = None
    
    def __post_init__(self):
        if self.num_filters is None:
            self.num_filters = [64, 128, 256, 512]
        if self.kernel_sizes is None:
            self.kernel_sizes = [3, 3, 3, 3]


class EarthDataset(Dataset):
    """Dataset for Earth observation data"""
    
    def __init__(
        self,
        X: Union[np.ndarray, torch.Tensor],
        y: Union[np.ndarray, torch.Tensor],
        transform: Optional[Any] = None
    ):
        self.X = torch.FloatTensor(X) if isinstance(X, np.ndarray) else X
        self.y = torch.LongTensor(y) if isinstance(y, np.ndarray) else y
        self.transform = transform
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        x = self.X[idx]
        y = self.y[idx]
        
        if self.transform:
            x = self.transform(x)
        
        return x, y


class PatchDataset(Dataset):
    """Dataset for image patches (CNN training)"""
    
    def __init__(
        self,
        patches: List[np.ndarray],
        labels: List[int],
        augment: bool = True
    ):
        self.patches = patches
        self.labels = labels
        self.augment = augment
    
    def __len__(self):
        return len(self.patches)
    
    def __getitem__(self, idx):
        patch = self.patches[idx]
        label = self.labels[idx]
        
        # Convert to tensor (H, W, C) -> (C, H, W)
        if patch.ndim == 3:
            patch = np.transpose(patch, (2, 0, 1))
        else:
            patch = patch[np.newaxis, ...]
        
        x = torch.FloatTensor(patch)
        y = torch.LongTensor([label])[0]
        
        # Data augmentation
        if self.augment:
            x = self._augment(x)
        
        return x, y
    
    def _augment(self, x: torch.Tensor) -> torch.Tensor:
        """Apply random augmentations"""
        # Random horizontal flip
        if torch.rand(1) > 0.5:
            x = torch.flip(x, dims=[-1])
        
        # Random vertical flip
        if torch.rand(1) > 0.5:
            x = torch.flip(x, dims=[-2])
        
        # Random rotation (90, 180, 270)
        if torch.rand(1) > 0.5:
            k = torch.randint(1, 4, (1,)).item()
            x = torch.rot90(x, k=k, dims=[-2, -1])
        
        # Add Gaussian noise
        if torch.rand(1) > 0.7:
            noise = torch.randn_like(x) * 0.01
            x = x + noise
        
        return x


class TimeSeriesDataset(Dataset):
    """Dataset for time series data (LSTM/Transformer training)"""
    
    def __init__(
        self,
        sequences: np.ndarray,
        labels: np.ndarray,
        window_size: int = 30,
        stride: int = 1
    ):
        self.sequences = sequences
        self.labels = labels
        self.window_size = window_size
        self.stride = stride
    
    def __len__(self):
        return (len(self.sequences) - self.window_size) // self.stride + 1
    
    def __getitem__(self, idx):
        start = idx * self.stride
        end = start + self.window_size
        
        x = torch.FloatTensor(self.sequences[start:end])
        y = torch.LongTensor([self.labels[end - 1]])[0]
        
        return x, y


# ==================== CNN Models ====================

class UNet(nn.Module):
    """U-Net for semantic segmentation (landslide detection, land cover)"""
    
    def __init__(
        self,
        in_channels: int = 12,
        num_classes: int = 2,
        features: List[int] = None
    ):
        super().__init__()
        
        if features is None:
            features = [64, 128, 256, 512]
        
        self.encoder = nn.ModuleList()
        self.decoder = nn.ModuleList()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Encoder
        for feature in features:
            self.encoder.append(self._conv_block(in_channels, feature))
            in_channels = feature
        
        # Decoder
        for feature in reversed(features):
            self.decoder.append(
                nn.ConvTranspose2d(feature * 2, feature, kernel_size=2, stride=2)
            )
            self.decoder.append(self._conv_block(feature * 2, feature))
        
        # Bottleneck
        self.bottleneck = self._conv_block(features[-1], features[-1] * 2)
        
        # Final convolution
        self.final_conv = nn.Conv2d(features[0], num_classes, kernel_size=1)
    
    def _conv_block(self, in_channels: int, out_channels: int):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        skip_connections = []
        
        # Encoder path
        for down in self.encoder:
            x = down(x)
            skip_connections.append(x)
            x = self.pool(x)
        
        # Bottleneck
        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]
        
        # Decoder path
        for idx in range(0, len(self.decoder), 2):
            x = self.decoder[idx](x)
            skip_connection = skip_connections[idx // 2]
            
            # Handle size mismatch
            if x.shape != skip_connection.shape:
                x = F.interpolate(x, size=skip_connection.shape[2:], mode='bilinear', align_corners=True)
            
            concat_skip = torch.cat((skip_connection, x), dim=1)
            x = self.decoder[idx + 1](concat_skip)
        
        return self.final_conv(x)


class ResNetBlock(nn.Module):
    """Residual block for ResNet"""
    
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride),
                nn.BatchNorm2d(out_channels)
            )
    
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet(nn.Module):
    """ResNet for image classification (landslide, land cover classification)"""
    
    def __init__(
        self,
        in_channels: int = 12,
        num_classes: int = 2,
        num_blocks: List[int] = None,
        num_filters: List[int] = None
    ):
        super().__init__()
        
        if num_blocks is None:
            num_blocks = [2, 2, 2, 2]
        if num_filters is None:
            num_filters = [64, 128, 256, 512]
        
        self.conv1 = nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        self.layers = nn.ModuleList()
        in_channels = 64
        
        for num_block, num_filter in zip(num_blocks, num_filters):
            layer = self._make_layer(in_channels, num_filter, num_block, stride=2 if len(self.layers) > 0 else 1)
            self.layers.append(layer)
            in_channels = num_filter
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(num_filters[-1], num_classes)
    
    def _make_layer(self, in_channels: int, out_channels: int, num_blocks: int, stride: int = 1):
        layers = []
        layers.append(ResNetBlock(in_channels, out_channels, stride))
        for _ in range(1, num_blocks):
            layers.append(ResNetBlock(out_channels, out_channels))
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.maxpool(x)
        
        for layer in self.layers:
            x = layer(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x


# ==================== LSTM Models ====================

class LSTMModel(nn.Module):
    """LSTM for time series forecasting (climate prediction, weather)"""
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 256,
        num_layers: int = 4,
        num_classes: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = True
    ):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size * (2 if bidirectional else 1),
            num_heads=8,
            dropout=dropout,
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * (2 if bidirectional else 1), hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes)
        )
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Self-attention
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Global average pooling
        pooled = torch.mean(attn_out, dim=1)
        
        # Classification
        out = self.fc(pooled)
        return out


# ==================== Transformer Models ====================

class PositionalEncoding(nn.Module):
    """Positional encoding for Transformer"""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)


class EarthTransformer(nn.Module):
    """Transformer for Earth system modeling"""
    
    def __init__(
        self,
        input_size: int,
        d_model: int = 256,
        nhead: int = 8,
        num_encoder_layers: int = 6,
        num_decoder_layers: int = 4,
        dim_feedforward: int = 1024,
        dropout: float = 0.1,
        num_classes: int = 2,
        max_seq_length: int = 1000
    ):
        super().__init__()
        
        self.d_model = d_model
        
        # Input embedding
        self.input_embedding = nn.Linear(input_size, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, max_len=max_seq_length, dropout=dropout)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        
        # Transformer decoder (for sequence-to-sequence tasks)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_decoder_layers)
        
        # Output heads
        self.classification_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, num_classes)
        )
        
        self.regression_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1)
        )
    
    def forward(self, x, task: str = "classification"):
        # x shape: (batch, seq_len, input_size)
        
        # Embed input
        x = self.input_embedding(x) * np.sqrt(self.d_model)
        
        # Add positional encoding
        x = self.pos_encoder(x)
        
        # Transformer encoding
        memory = self.transformer_encoder(x)
        
        # Global average pooling
        pooled = torch.mean(memory, dim=1)
        
        # Task-specific head
        if task == "classification":
            return self.classification_head(pooled)
        elif task == "regression":
            return self.regression_head(pooled)
        else:
            raise ValueError(f"Unknown task: {task}")


# ==================== Training Pipeline ====================

class Trainer:
    """Universal trainer for all model types"""
    
    def __init__(self, config: TrainingConfig, model_name: str = "model"):
        self.config = config
        self.model_name = model_name
        self.device = torch.device(config.device)
        self.scaler = torch.cuda.amp.GradScaler() if config.mixed_precision else None
        
        # Tracking
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.current_epoch = 0
        
        # Initialize wandb
        if wandb is not None:
            try:
                wandb.init(project="earth-ai-platform", name=model_name)
                wandb.config.update(config.__dict__)
            except Exception:
                logger.warning("WandB initialization failed")
    
    def train(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        criterion: nn.Module = None,
        optimizer: torch.optim.Optimizer = None,
        scheduler: Any = None
    ) -> Dict[str, List[float]]:
        """Train model with validation"""
        
        model = model.to(self.device)
        
        if criterion is None:
            criterion = nn.CrossEntropyLoss()
        
        if optimizer is None:
            optimizer = AdamW(
                model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        
        if scheduler is None:
            scheduler = ReduceLROnPlateau(
                optimizer,
                mode='min',
                patience=5,
                factor=0.5,
                verbose=True
            )
        
        history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
        
        for epoch in range(self.config.epochs):
            self.current_epoch = epoch
            
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(self.device), target.to(self.device)
                
                optimizer.zero_grad()
                
                # Mixed precision training
                if self.scaler:
                    with torch.cuda.amp.autocast():
                        output = model(data)
                        loss = criterion(output, target)
                    
                    self.scaler.scale(loss).backward()
                    
                    # Gradient clipping
                    if self.config.gradient_clip > 0:
                        self.scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), self.config.gradient_clip)
                    
                    self.scaler.step(optimizer)
                    self.scaler.update()
                else:
                    output = model(data)
                    loss = criterion(output, target)
                    loss.backward()
                    
                    if self.config.gradient_clip > 0:
                        torch.nn.utils.clip_grad_norm_(model.parameters(), self.config.gradient_clip)
                    
                    optimizer.step()
                
                train_loss += loss.item()
                _, predicted = output.max(1)
                train_total += target.size(0)
                train_correct += predicted.eq(target).sum().item()
                
                if batch_idx % 10 == 0:
                    logger.info(f"Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item():.4f}")
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(self.device), target.to(self.device)
                    
                    if self.scaler:
                        with torch.cuda.amp.autocast():
                            output = model(data)
                            loss = criterion(output, target)
                    else:
                        output = model(data)
                        loss = criterion(output, target)
                    
                    val_loss += loss.item()
                    _, predicted = output.max(1)
                    val_total += target.size(0)
                    val_correct += predicted.eq(target).sum().item()
            
            # Calculate metrics
            train_loss_avg = train_loss / len(train_loader)
            val_loss_avg = val_loss / len(val_loader)
            train_acc = 100. * train_correct / train_total
            val_acc = 100. * val_correct / val_total
            
            history["train_loss"].append(train_loss_avg)
            history["val_loss"].append(val_loss_avg)
            history["train_acc"].append(train_acc)
            history["val_acc"].append(val_acc)
            
            logger.info(
                f"Epoch {epoch}/{self.config.epochs}: "
                f"Train Loss: {train_loss_avg:.4f}, Val Loss: {val_loss_avg:.4f}, "
                f"Train Acc: {train_acc:.2f}%, Val Acc: {val_acc:.2f}%"
            )
            
            # Log to wandb
            if wandb is not None:
                try:
                    wandb.log({
                        "train_loss": train_loss_avg,
                        "val_loss": val_loss_avg,
                        "train_acc": train_acc,
                        "val_acc": val_acc,
                        "learning_rate": optimizer.param_groups[0]['lr']
                    })
                except Exception:
                    pass
            
            # Learning rate scheduling
            scheduler.step(val_loss_avg)
            
            # Early stopping
            if val_loss_avg < self.best_val_loss:
                self.best_val_loss = val_loss_avg
                self.patience_counter = 0
                self.save_checkpoint(model, optimizer, scheduler, epoch, "best")
            else:
                self.patience_counter += 1
                if self.patience_counter >= self.config.early_stopping_patience:
                    logger.info(f"Early stopping triggered at epoch {epoch}")
                    break
            
            # Save checkpoint periodically
            if epoch % 10 == 0:
                self.save_checkpoint(model, optimizer, scheduler, epoch, f"epoch_{epoch}")
        
        return history
    
    def evaluate(
        self,
        model: nn.Module,
        test_loader: DataLoader,
        criterion: nn.Module = None
    ) -> Dict[str, float]:
        """Evaluate model on test set"""
        
        model = model.to(self.device)
        model.eval()
        
        if criterion is None:
            criterion = nn.CrossEntropyLoss()
        
        test_loss = 0.0
        all_predictions = []
        all_targets = []
        all_probabilities = []
        
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(self.device), target.to(self.device)
                
                output = model(data)
                loss = criterion(output, target)
                
                test_loss += loss.item()
                probabilities = F.softmax(output, dim=1)
                _, predicted = output.max(1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_targets.extend(target.cpu().numpy())
                all_probabilities.extend(probabilities[:, 1].cpu().numpy())
        
        # Calculate metrics
        test_loss_avg = test_loss / len(test_loader)
        accuracy = accuracy_score(all_targets, all_predictions)
        f1 = f1_score(all_targets, all_predictions, average='weighted')
        
        try:
            auc = roc_auc_score(all_targets, all_probabilities)
        except:
            auc = 0.0
        
        metrics = {
            "test_loss": test_loss_avg,
            "accuracy": accuracy,
            "f1_score": f1,
            "auc": auc
        }
        
        logger.info(f"Test Results: Loss={test_loss_avg:.4f}, Acc={accuracy:.4f}, F1={f1:.4f}, AUC={auc:.4f}")
        
        return metrics
    
    def save_checkpoint(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Any,
        epoch: int,
        name: str
    ):
        """Save model checkpoint"""
        
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
            "config": self.config.__dict__,
            "train_losses": self.train_losses,
            "val_losses": self.val_losses
        }
        
        path = Path(f"./models/checkpoints/{self.model_name}_{name}.pt")
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved: {path}")
    
    def load_checkpoint(
        self,
        model: nn.Module,
        path: str
    ) -> nn.Module:
        """Load model from checkpoint"""
        
        checkpoint = torch.load(path, map_location=self.device)
        model.load_state_dict(checkpoint["model_state_dict"])
        model = model.to(self.device)
        
        logger.info(f"Checkpoint loaded: {path}")
        return model


# ==================== Model Factory ====================

class ModelFactory:
    """Factory for creating models based on task type"""
    
    @staticmethod
    def create_model(
        model_type: str,
        config: TrainingConfig,
        **kwargs
    ) -> nn.Module:
        """Create model based on type"""
        
        if model_type.lower() == "unet":
            return UNet(
                in_channels=config.input_channels,
                num_classes=config.num_classes,
                **kwargs
            )
        
        elif model_type.lower() == "resnet":
            return ResNet(
                in_channels=config.input_channels,
                num_classes=config.num_classes,
                **kwargs
            )
        
        elif model_type.lower() == "lstm":
            return LSTMModel(
                input_size=config.input_channels,
                hidden_size=config.hidden_dim,
                num_layers=config.num_layers,
                num_classes=config.num_classes,
                dropout=config.dropout,
                **kwargs
            )
        
        elif model_type.lower() == "transformer":
            return EarthTransformer(
                input_size=config.input_channels,
                d_model=config.hidden_dim,
                nhead=config.num_heads,
                num_encoder_layers=config.num_layers,
                dim_feedforward=config.dim_feedforward,
                dropout=config.dropout,
                num_classes=config.num_classes,
                **kwargs
            )
        
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    @staticmethod
    def create_dataset(
        data_type: str,
        X: np.ndarray,
        y: np.ndarray,
        **kwargs
    ) -> Dataset:
        """Create dataset based on data type"""
        
        if data_type == "tabular":
            return EarthDataset(X, y)
        
        elif data_type == "image_patches":
            return PatchDataset(X, y, **kwargs)
        
        elif data_type == "time_series":
            return TimeSeriesDataset(X, y, **kwargs)
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")


# Example usage
if __name__ == "__main__":
    # Create sample data
    batch_size = 4
    channels = 12
    height, width = 256, 256
    
    # Sample image data (for CNN)
    X_images = np.random.randn(100, channels, height, width).astype(np.float32)
    y_images = np.random.randint(0, 2, 100)
    
    # Create dataset and dataloader
    dataset = EarthDataset(X_images, y_images)
    train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    
    # Create model
    config = TrainingConfig(model_type="resnet", input_channels=channels)
    model = ModelFactory.create_model("resnet", config)
    
    # Train
    trainer = Trainer(config, model_name="resnet_demo")
    history = trainer.train(model, train_loader, val_loader)
    
    # Evaluate
    metrics = trainer.evaluate(model, val_loader)
    print(f"Test Metrics: {metrics}")
