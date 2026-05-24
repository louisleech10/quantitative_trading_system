"""One-off: list all datasets in feature_klines/kline_cache.h5."""
import h5py

path = "/Users/louis/Desktop/quantitative_trading_system/data_cache/feature_klines/kline_cache.h5"
with h5py.File(path, "r") as f:
    def walk(name, obj):
        if isinstance(obj, h5py.Dataset):
            fields = obj.dtype.names
            print(f"{name}\tshape={obj.shape}\tfields={fields}")
    f.visititems(walk)
