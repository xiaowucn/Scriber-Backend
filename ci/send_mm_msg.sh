#!/bin/bash

if [ -d .git ]; then
    BRANCH_NAME="($(git rev-parse --abbrev-ref HEAD))"
fi

bash /data/ci/fitout/autodoc/send_mm_msg.sh http://mm.paodingai.com/hooks/xffd4wkndpnjubqd9z9puzoxaa labelsystem \[Label测试环境\]\(http://tl.paodingai.com\)\ 因果关系\|PDF标注\|PDF上下文标注\|高管简历标注\|PDF目录标注\|PDF元素块标注\ 后端已更新至版本\:\`${GO_REVISION_REMARKABLE:0:8}${BRANCH_NAME}\`
