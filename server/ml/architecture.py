"""
Shared model architecture and preprocessing for Rill's visual embedding
model. Imported by BOTH ml/training/train.py (to train it) and
ml/inference.py (to load and run it at inference time) — this is the single
source of truth for the network shape and image preprocessing, so training
and inference can never silently drift apart (a very easy bug to introduce
if these were defined twice).

StreamEmbeddingNet: a ResNet18 backbone (ImageNet-pretrained as a starting
point — standard transfer learning practice) with its classification head
replaced by a small projection to a 128-dim embedding, L2-normalized so
cosine similarity behaves well. This is trained with triplet loss (see
ml/training/train.py) rather than used as-is — an untrained/frozen ImageNet
backbone has no reason to place two different-looking stream photos close
together just because they're both streams; triplet training (see
ml/training/train.py) is what actually teaches "these look similar, those
don't."
"""

EMBEDDING_DIM = 128
IMAGE_SIZE = 128

# Standard ImageNet normalization stats — kept since the backbone starts
# from ImageNet-pretrained weights, even though it's later fine-tuned on
# the synthetic dataset.
NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]


def get_transform():
    """
    The exact preprocessing pipeline used for every image, at training time
    and at inference time alike. Must stay identical between the two, or
    embeddings computed live won't mean the same thing as the ones the
    model was trained on.
    """
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
        ]
    )


def build_model(embedding_dim: int = EMBEDDING_DIM, pretrained: bool = True):
    """
    pretrained=True: initialize the backbone from ImageNet weights (needs
    internet on first call — used at training time).
    pretrained=False: random init (used when loading a checkpoint, since
    the checkpoint's saved weights will overwrite the backbone anyway —
    avoids an unnecessary weight download just to immediately discard it).
    """
    if pretrained:
        import os
        import ssl
        try:
            import certifi
            os.environ.setdefault("SSL_CERT_FILE", certifi.where())
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass

    import torch.nn as nn
    from torchvision.models import ResNet18_Weights, resnet18

    weights = ResNet18_Weights.DEFAULT if pretrained else None
    backbone = resnet18(weights=weights)
    feature_extractor = nn.Sequential(*list(backbone.children())[:-1])  # drop the 1000-class head

    class StreamEmbeddingNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = feature_extractor
            self.projection = nn.Linear(512, embedding_dim)

        def forward(self, x):
            features = self.backbone(x).flatten(1)  # (batch, 512)
            embedding = self.projection(features)  # (batch, embedding_dim)
            return nn.functional.normalize(embedding, dim=1)

    return StreamEmbeddingNet()
