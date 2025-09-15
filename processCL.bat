@echo off
REM ===== 옵션 =====
setlocal enabledelayedexpansion

REM 
REM 
CALL conda activate centerline 2>nul

REM ---- 인자 파싱 ----
set "file="
set "index="
set "cellID="

:parse
if "%~1"=="" goto after_parse

if "%~1"=="--file" (
    set "file=%~2"
    shift
) else if "%~1"=="--index" (
    set "index=%~2"
    shift
) else if "%~1"=="--cellID" (
    set "cellID=%~2"
    shift
) else if "%~1"=="--advancementRatio" (
    set "advancementRatio=%~2"
    shift
) else (
    echo Unknown parameter: %~1
    exit /b 1
)
shift
goto parse

:after_parse
echo 파일: %file%
echo 인덱스: %index%
echo cellID: %cellID%

REM ---- 경로 설정 ----
set "PY_PATH=processCL.py"

echo ➡ python 스크립트 실행
python --version
python "%PY_PATH%" --file "%file%" --index "%index%" --cellID "%cellID%" --advancementRatio "%advancementRatio%"

endlocal
