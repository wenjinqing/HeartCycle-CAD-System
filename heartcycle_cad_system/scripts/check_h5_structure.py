import h5py
import numpy as np

h5_path = r'D:\Graduate Work\heartcycle\59146237\measure\CH07_59146237_s0000029.h5'

print("=" * 60)
print("H5 File Structure Analysis")
print("=" * 60)
print(f"File: {h5_path}")
print()

with h5py.File(h5_path, 'r') as f:
    def print_structure(name, obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, h5py.Dataset):
            print(f"{prefix}[Dataset] {name}")
            print(f"{prefix}  - shape: {obj.shape}")
            print(f"{prefix}  - dtype: {obj.dtype}")
            print(f"{prefix}  - size: {obj.size}")

            # 显示数据示例
            if obj.size <= 10:
                print(f"{prefix}  - value: {obj[()]}")
            elif obj.size <= 100:
                print(f"{prefix}  - first 10: {obj[:10]}")
            else:
                print(f"{prefix}  - first 5: {obj[:5]}")
                print(f"{prefix}  - stats: min={np.min(obj[:]):.2f}, max={np.max(obj[:]):.2f}, mean={np.mean(obj[:]):.2f}")
        elif isinstance(obj, h5py.Group):
            print(f"{prefix}[Group] {name}")
            print(f"{prefix}  - keys: {list(obj.keys())}")

    print("Root level:")
    print(f"  Keys: {list(f.keys())}")
    print()

    print("Full structure:")
    f.visititems(print_structure)

    # 特别检查measure组
    if 'measure' in f:
        print("\n" + "=" * 60)
        print("Detailed measure group analysis:")
        print("=" * 60)
        g = f['measure']
        for key in g.keys():
            item = g[key]
            print(f"\n{key}:")
            if isinstance(item, h5py.Dataset):
                print(f"  Shape: {item.shape}")
                print(f"  Dtype: {item.dtype}")
                print(f"  Value: {item[()]}")
            else:
                print(f"  Type: Group with keys {list(item.keys())}")
