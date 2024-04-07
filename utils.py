def format_tag(original_tag: str):
    modified_tag = original_tag

    # in a character tag for example character_(series), we need to remove the series part
    if "(" in original_tag:
        modified_tag = original_tag.split("(")[0]

    # remove underscores
    modified_tag = modified_tag.replace("_", " ")

    # trim leading and trailing whitespaces
    modified_tag = modified_tag.strip()

    # capitalize the first letter of each word
    modified_tag = modified_tag.title()

    return modified_tag

def str_list_to_str(list: list[str]):
    return ', '.join(['"' + item + '"' for item in list])

def int_list_to_str(list: list[int]):
    return ",".join(str(x) for x in list)