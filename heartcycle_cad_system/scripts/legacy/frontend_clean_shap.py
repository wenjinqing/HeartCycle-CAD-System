#!/usr/bin/env python3
"""
清理ShapExplanation.vue文件，删除旧的ECharts初始化代码
"""

def clean_shap_explanation():
    file_path = r"D:\Graduate Work\heartcycle_cad_system\frontend\src\components\ShapExplanation.vue"

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到需要删除的行范围
    # 从 "// 更新表格数据" 后面的错误代码开始删除到 "// 监听props变化" 之前

    new_lines = []
    skip_mode = False
    skip_start = None

    for i, line in enumerate(lines, 1):
        # 检测到错误的代码块开始（行513的if语句）
        if i == 513 and 'if (!globalChartRef.value' in line:
            skip_mode = True
            skip_start = i
            continue

        # 检测到正确的代码块开始（行903的"// 更新表格数据"）
        if i == 903 and '// 更新表格数据' in line:
            skip_mode = False
            new_lines.append(line)
            continue

        # 跳过模式下不添加行
        if skip_mode:
            continue

        new_lines.append(line)

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("File cleaned successfully")
    print(f"Deleted lines {skip_start} to 902")
    print(f"Original: {len(lines)} lines")
    print(f"New: {len(new_lines)} lines")
    print(f"Reduced: {len(lines) - len(new_lines)} lines")

if __name__ == '__main__':
    clean_shap_explanation()
