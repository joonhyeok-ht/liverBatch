#!/bin/bash

# Conda 환경 초기화 (기존에 init 되어있어야 함)
source $(conda info --base)/etc/profile.d/conda.sh

# Conda 가상환경 활성화
conda activate centerline

# 인자 처리
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --file) file="$2"; shift ;;
        --index) index="$2"; shift ;;
        --cellID) cellID="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# 인자 확인
echo "파일: $file"
echo "인덱스: $index"
echo "cellID: $cellID"

# Python 버전 확인
python --version

# Python 스크립트 실행 (인자 포함)
python C:/Users/hutom/Desktop/jh_test/CommonPipelines/CommonPipeline_10_sco/CommonPipeline_10/processCL.py --file "$file" --index "$index" --cellID "$cellID"


# Python 버전 확인
# python --version
# python /Users/hutom/Desktop/solution/project/anaconda/Solution/UnitTestPrev/CommonPipeline_10/processCL.py
# cd /Users/hutom/Desktop/solution/project/anaconda/Solution/UnitTestPrev/CommonPipeline_10/
pwd