#!/bin/bash

# 前后端对齐检查脚本

echo "======================================"
echo "HeartCycle 前后端对齐检查"
echo "======================================"
echo ""

# 检查后端文件
echo "📋 检查后端文件..."
echo ""

files=(
    "backend/algorithms/advanced_preprocessing.py"
    "backend/algorithms/advanced_feature_engineering.py"
    "backend/algorithms/dataset_generator.py"
    "backend/algorithms/enhanced_shap_analysis.py"
    "backend/algorithms/experiment_evaluation.py"
    "backend/app/api/v1/experiment.py"
    "backend/run_experiment.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (缺失)"
    fi
done

echo ""
echo "📋 检查前端文件..."
echo ""

frontend_files=(
    "frontend/src/views/ThesisExperiment.vue"
    "frontend/src/router/index.js"
    "frontend/src/App.vue"
)

for file in "${frontend_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (缺失)"
    fi
done

echo ""
echo "📋 检查数据文件..."
echo ""

if [ -f "data/cad_dataset_10k.csv" ]; then
    echo "✅ data/cad_dataset_10k.csv"
    lines=$(wc -l < "data/cad_dataset_10k.csv")
    echo "   样本数: $((lines - 1))"
else
    echo "❌ data/cad_dataset_10k.csv (缺失)"
    echo "   请运行: cd backend/algorithms && python dataset_generator.py"
fi

echo ""
echo "📋 检查文档..."
echo ""

docs=(
    "docs/thesis/README_THESIS.md"
    "docs/thesis/THESIS_COMPLETE_GUIDE.md"
    "docs/thesis/THESIS_IMPLEMENTATION_SUMMARY.md"
    "docs/history/FRONTEND_BACKEND_ALIGNMENT.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ $doc"
    else
        echo "❌ $doc (缺失)"
    fi
done

echo ""
echo "======================================"
echo "检查完成！"
echo "======================================"
echo ""

# 检查Python依赖
echo "📦 检查Python依赖..."
echo ""

python_deps=(
    "pandas"
    "numpy"
    "scikit-learn"
    "xgboost"
    "lightgbm"
    "shap"
    "imblearn"
)

for dep in "${python_deps[@]}"; do
    if python -c "import $dep" 2>/dev/null; then
        echo "✅ $dep"
    else
        echo "❌ $dep (未安装)"
    fi
done

echo ""
echo "🚀 启动建议:"
echo ""
echo "1. 后端: cd backend && python -m uvicorn app.main:app --reload"
echo "2. 前端: cd frontend && npm run dev"
echo "3. 访问: http://localhost:5173"
echo "4. 登录后点击'论文实验'菜单"
echo ""
