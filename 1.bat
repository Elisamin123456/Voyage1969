@echo off
REM === 设置 Git 用户信息（如果未配置全局） ===
git config --global user.name "YourGitHubUsername"
git config --global user.email "YourEmail@example.com"

REM === 设置仓库地址 ===
set REPO_URL=https://github.com/Elisamin123456/Voyage1969.git

REM === 初始化 git 仓库（如果尚未初始化） ===
IF NOT EXIST ".git" (
    echo 初始化 git 仓库...
    git init
    git remote add origin %REPO_URL%
) ELSE (
    echo 已初始化 git 仓库，更新远程地址...
    git remote set-url origin %REPO_URL%
)

REM === 添加所有文件 ===
echo 添加文件...
git add .

REM === 提交更改 ===
set /p COMMIT_MSG=请输入提交说明（默认: "Auto commit"）： 
IF "%COMMIT_MSG%"=="" set COMMIT_MSG=Auto commit
git commit -m "%COMMIT_MSG%"

REM === 推送到远程仓库 ===
echo 推送中...
git branch -M main
git push -u origin main

pause
