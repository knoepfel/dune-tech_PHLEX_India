# Machine learning for DUNE: practical tutorials

This is the 90-minute practical introduced on slide 9 of *Machine Learning for DUNE* (28 October 2026). Start with the mechanics of training, then classify the same MiniLAr particle images with an MLP and a CNN. The broader lecture also covers segmentation, graph networks, transformers, and foundation models; implementing those is outside this practical.

## Before the session

Open the workshop [Linux JupyterHub](https://dune-tech.rice.edu/jupyterhub) and select the **physics-ml** tile. Use the **physics-ml** kernel for all tutorials. The notebooks use `torch`, `numpy`, `matplotlib`, `pandas`, and `tqdm`. Basic Python, arrays, and familiarity with the lecture's model/loss/gradient terminology are sufficient. CUDA is optional: the notebooks select it when available and otherwise use CPU.

Open the three main notebooks from `tutorial-ml/` and run each from top to bottom in a fresh kernel. Keep `dataset/`, `weights/`, `logs_mlp/`, `logs_cnn/`, and `inference/` alongside them. The image notebooks use four Linux data-loader workers; lower `num_workers` if your Hub allocation has limited CPU or RAM.

MiniLAr downloads about 151 MiB on first use and creates a reusable cache in `dataset/minilar-dataset/`. Allow additional disk/RAM for the processed tensors. For an offline Hub, preload `dataset/minilar-dataset/raw/lartpc_particles.pt`, or set `DATA_URL` to a local copy. Use the same cache and split settings in both image notebooks. Existing processed files are reused: changing the split seed/fraction requires a new cache directory.

## Suggested 90-minute route

The session alternates instructor-led fill-ins with an independent challenge. **01 and 02 intentionally do not run unchanged:** each has six numbered `missing(...)` stops in the main execution path. Students call out the missing expression or line, the instructor fills it in, and everyone reruns that cell. Allow 15–45 seconds per stop; this is not a series of open-ended coding exercises. Other prompts are brief discussion points. All API names are supplied before a gap. Students infer dimensions, array axes, prediction/target roles, booleans, or operation order from the preceding explanation; they do not need to recall PyTorch vocabulary.

| Time | Notebook | Core activity | Lecture connection |
| --- | --- | --- | --- |
| 0–5 min | Setup | Select `physics-ml`; check imports and preloaded data | Practical roadmap, slide 9 |
| 5–25 min | [01: Training Basics](ML-01-TrainingBasics.ipynb) | Six live fill-ins; ring classification; training vs validation | Optimization, slides 25–29; generalization, 35–40; networks/backpropagation, 45–67 |
| 25–50 min | [02: MiniLAr + MLP](ML-02-MLP.ipynb) | Six live fill-ins; short training demo; reference-model accuracy/confusion matrix | MLPs, slides 56–58; flattening, 77–79; MiniLAr, 97 |
| 50–80 min | [03: MiniLAr + CNN](ML-03-CNN.ipynb) | Independent work: build model, implement update, predict, explain confusion | Convolutions/pooling, slides 80–94; MiniLAr, 97 |
| 80–90 min | Debrief and buffer | Compare measured mistakes, training budgets, and explanations | Generalization and model comparison |

**Ninety minutes is a focused route, not time to cover every cell.** It assumes basic Python familiarity and a working Hub/data cache. Skim 01's framework overview/GPU benchmark and defer its Exercises A–C. In 02, inspect an image, then jump to section 2.2; the toy `DataLoader` examples in sections 2.0–2.1 are optional and can be skipped safely. Defer Exercises A–D (width, timing, parameter counts). Reach the MLP confusion matrix and hand over to 03 at minute 50. If running late, cut optional discussion rather than the independent work. A full walkthrough with all extensions needs another session.

In 02, `USE_PRETRAINED=True` is the live default: run a 20-step demonstration, then load the supplied MLP and its matching reference log. Those final metrics describe the supplied weights, not the demonstration. Use `False` for a full 10,000-step run after the session.

In 03, students complete four tasks with syntax references and executable checks: connect layer dimensions, assemble a training step from a supplied line bank, choose inference inputs/axes, and normalize a confusion matrix. The challenge is to apply the earlier concepts, not to discover new library calls. The supplied training loop runs their optimizer step for **10,000 mini-batches**, without a time cutoff. The instructor measured **24 seconds** for this run on the workshop machine; runtime can vary with session resources. The core result is **their own trained CNN**. After completing the update check and training run, they may set `USE_REFERENCE_WEIGHTS=True` to inspect the long-trained CNN; they still implement the predictions and confusion matrix. No cached CNN predictions bypass those tasks.

**Handoff at minute 50:** “Keep 02 open as a reference and start 03 with a fresh kernel. Build a CNN that passes the shape check, train it, calculate its accuracy and confusion matrix, and tell us one important mistake. Ask for a hint after two minutes stuck. High accuracy is not the completion criterion.”

The default CNN run and reference MLP both use 10,000 steps with batches of 64. The debrief should discuss remaining differences such as initialization and model capacity; one run does not establish a robust architecture comparison. Ask participants to report the weights/run they used, one per-class recall, one common confusion, and a limitation of the comparison.

## What the data and scores mean

MiniLAr has one `[1, 28, 28]` floating-point image and one integer species label per example: **0 electron, 1 muon, 2 pion, 3 proton, 4 kaon**. It is a simplified projected particle-image classification task, not full DUNE event reconstruction, neutrino-flavor classification, or pixel segmentation. Projection, cropping, and clipping can remove physical information.

The binary toy model produces one logit and uses `BCEWithLogitsLoss`. The image models produce five logits and use `CrossEntropyLoss` with integer targets; softmax is applied only for inference. Flattening preserves pixel values and ordering. A CNN instead builds in local connectivity and weight sharing; it need not outperform an MLP on every dataset.

The wrapper defaults to a reproducible random **80/20 split**, unlike slide 40's illustrative 80/10/10 workflow. Its API calls the second split `test`, but using it repeatedly to compare architectures makes it a **validation set**. A final research evaluation needs a separate untouched test set. Related views of the same physical event must stay in one split; the wrapper does not implement event-group splitting.

Use fresh inference when evaluating your own weights. Optional cached predictions in `inference/` describe the bundled models only; replacing fresh predictions with them would invalidate a model comparison.

## Optional data material

[dataset/LArTPC-DataLoading.ipynb](dataset/LArTPC-DataLoading.ipynb) is a standalone data preview, not a fourth required tutorial. Open it from `tutorial-ml/dataset/`; it shares the main notebooks' `minilar-dataset/` cache.

`dataset/convert_lartpc_images.py` is a preparation utility for sparse particle chunks, not part of the student route. Run it with `--help` for projection/crop/energy settings. Each input chunk must contain one particle species (either charge sign). Its defaults use a fixed detector projection; global-PCA options fit geometry from their input sample, so research train/test preprocessing requires care to avoid leakage. The supplied weights correspond to the workshop dataset, not arbitrary regenerated images.

## Instructor solutions and release

Completed copies of 01–03 are kept locally in `solution/`, with a quick answer key and worked optional exercises. The directory is ignored by Git so a normal add/commit will not publish it before the session. Ignore rules are not access control: do not upload or copy that directory to the student Hub or include it in a workshop ZIP before release.

After the session, remove `/solution/` from `tutorial-ml/.gitignore` and add the solution directory in your normal release commit. The solution notebooks resolve the parent directory for shared data/weights and can be opened directly from `tutorial-ml/solution/`.

## Similar-size model comparison

The default MLP now has **32 hidden neurons and 25,285 parameters**, versus **23,621 parameters** for the CNN. Both reference models use 10,000 optimizer steps, batches of 64, and Adam with learning rate 0.001 on the same split.

The updated bundled MLP reaches **64.84%** accuracy on the 9,992 held-out images; the supplied CNN reaches **75.62%**. The CNN has about 7% fewer parameters and scores 10.78 percentage points higher in this comparison. These are single-run reference results, not a guarantee across seeds. The MLP was retrained on CPU with PyTorch 2.8.0 and seed 12345. The checkpoint, log, and cached predictions all correspond to this 32-neuron model.
