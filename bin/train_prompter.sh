#!/bin/bash

MOLD=$1

inv prompter.load-data-v2 $MOLD --clear --update
inv prompter.extract-feature-v2 $MOLD
inv prompter.train-v2 $MOLD
inv op.prompt-element --mold=$MOLD --overwrite
python -m remarkable.optools.stat_scriber_answer -c -m $MOLD
