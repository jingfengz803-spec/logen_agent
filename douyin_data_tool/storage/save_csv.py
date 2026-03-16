import pandas as pd


def save_csv(data, file):

    df = pd.DataFrame(data)

    df.to_csv(
        file,
        index=False,
        encoding="utf_8_sig"
    )

    print("数据已保存:", file)