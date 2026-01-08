#!/bin/bash

MOLD=$1

inv predictor.prepare-dataset $MOLD
inv predictor.train $MOLD
inv op.preset-answer --mold=$MOLD --overwrite
python -m remarkable.optools.stat_scriber_answer -m $MOLD
