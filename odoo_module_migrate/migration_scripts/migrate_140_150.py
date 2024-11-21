# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re
from pathlib import Path
import lxml.etree as et
from odoo_module_migrate.base_migration_script import BaseMigrationScript


def _replace_t_esc_and_t_raw_with_t_out(file_path: Path):
    """
    Replaces `t-esc` and `t-raw` attributes with `t-out` in an XML file.

    Args:
        file_path (Path): Path to the XML file to process.

    Returns:
        Path: The updated file if changes were made, otherwise None.
    """
    parser = et.XMLParser(remove_blank_text=True)
    tree = et.parse(str(file_path.resolve()), parser)
    root = tree.getroot()

    # Find all elements with `t-esc` or `t-raw` attributes
    updated = False
    for elem in root.iter():
        for attr_name in ("t-esc", "t-raw"):
            if attr_name in elem.attrib:
                # Replace with `t-out`
                elem.set("t-out", elem.attrib.pop(attr_name))
                updated = True
    if updated:
        # Write back the modified XML
        file_path.write_text(
            et.tostring(tree, pretty_print=True, encoding="unicode")
        )
        return file_path
    return None


def _get_files(module_path, reformat_file_ext):
    """Get files to be reformatted."""
    file_paths = list()
    if not module_path.is_dir():
        raise Exception(f"'{module_path}' is not a directory")
    file_paths.extend(module_path.rglob("*" + reformat_file_ext))
    return file_paths


def reformat_deprecated_tags(
        logger, module_path, module_name, manifest_path, migration_steps, tools
):
    """Reformat deprecated tags in XML files.

    Deprecated tags are `t-esc` and `t-raw`:
    they have to be substituted by the `t-out` tag.
    """

    reformat_file_ext = ".xml"
    file_paths = _get_files(module_path, reformat_file_ext)
    logger.debug(f"{reformat_file_ext} files found:\n" f"{list(map(str, file_paths))}")

    reformatted_files = list()
    for file_path in file_paths:
        reformatted_file = _replace_t_esc_and_t_raw_with_t_out(file_path)
        if reformatted_file:
            reformatted_files.append(reformatted_file)
    logger.debug("Reformatted files:\n" f"{list(reformatted_files)}")


class MigrationScript(BaseMigrationScript):
    _GLOBAL_FUNCTIONS = [reformat_deprecated_tags]
