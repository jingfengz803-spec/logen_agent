def hot_score(item):
    like = item["like"]  # 若item中没有"like"键，会抛出KeyError
    comment = item["comment"]  # 同理
    share = item["share"]

    score = like + comment * 2 + share * 3
    return score
