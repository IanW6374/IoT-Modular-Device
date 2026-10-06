"""Exact release targeting owned by the Management command workflow."""


def for_target(releases, sequence=0, release_type=''):
    sequence = int(sequence or 0)
    return [item for item in releases if
            (not sequence or int(item.get('release_sequence', 0) or 0) == sequence) and
            (not release_type or str(item.get('type', '')) == str(release_type))]
