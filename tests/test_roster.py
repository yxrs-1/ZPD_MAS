import pytest

from scaffolding.roster import ImportFailure, Roster, RosterError


def test_the_teacher_starts_as_the_preset_account():
    roster = Roster()

    assert roster.authenticate_teacher("643590872", "643590872") is True
    assert roster.authenticate_teacher("643590872", "nope") is False
    assert roster.authenticate_student("643590872", "643590872") is None


def test_the_teacher_can_change_only_a_filled_new_password():
    roster = Roster()

    with pytest.raises(RosterError, match="原密码不正确"):
        roster.change_teacher_password("nope", "next")
    with pytest.raises(RosterError, match="密码不能为空"):
        roster.change_teacher_password("643590872", "  ")
    roster.change_teacher_password("643590872", " next ")

    assert roster.authenticate_teacher("643590872", "next") is True
    assert roster.teacher_account == "643590872"


def test_class_names_are_stripped_and_unique():
    roster = Roster()

    with pytest.raises(RosterError, match="先填写班级名称"):
        roster.create_class("  ")
    created = roster.create_class(" 一班 ")
    with pytest.raises(RosterError, match="已有同名班级"):
        roster.create_class("一班")

    assert created.class_id == "class-1"
    assert created.name == "一班"
    assert roster.classes() == (created,)


def test_import_keeps_valid_rows_and_reports_the_rest():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))

    result = roster.import_rows(second.class_id, (
        (2, "s2", "secret", "乙"),
        (3, "", "secret", "丙"),
        (4, "s3", "  ", "丁"),
        (5, "s4", "secret", "  "),
        (6, "s2", "other", "戊"),
        (7, "s1", "other", "己"),
        (8, "  ", " ", " "),
    ))

    assert [item.account for item in result.added] == ["s2"]
    assert [item.reason for item in result.failures] == [
        "账号或密码为空",
        "账号或密码为空",
        "姓名为空",
        "账号在这份表里重复",
        "账号已经存在",
    ]
    assert roster.authenticate_student("s1", "secret").class_id == first.class_id
    assert roster.authenticate_student("s1", "other") is None
    assert [item.name for item in roster.students(second.class_id)] == ["乙"]


def test_a_missing_field_on_the_first_copy_blocks_later_copies():
    roster = Roster()
    created = roster.create_class("一班")

    result = roster.import_rows(created.class_id, (
        (2, "s1", "", "甲"),
        (3, "s1", "secret", "乙"),
    ))

    assert result.added == ()
    assert [item.reason for item in result.failures] == ["账号或密码为空", "账号在这份表里重复"]


def test_a_missing_cell_is_reported_separately_from_a_blank_cell():
    roster = Roster()
    created = roster.create_class("一班")

    result = roster.import_rows(created.class_id, ((2, "s1", None, "甲"),))

    assert result.added == ()
    assert result.failures == (ImportFailure(2, "缺账号、密码或姓名"),)


def test_rename_reset_and_remove_keep_other_students():
    roster = Roster()
    created = roster.create_class("一班")
    roster.import_rows(created.class_id, ((2, "s1", "secret", "甲"), (3, "s2", "secret", "乙")))

    with pytest.raises(RosterError, match="姓名不能为空"):
        roster.rename_student(created.class_id, "s1", " ")
    roster.rename_student(created.class_id, "s1", " 甲一 ")
    with pytest.raises(RosterError, match="密码不能为空"):
        roster.reset_password(created.class_id, "s1", " ")
    roster.reset_password(created.class_id, "s1", " next ")
    removed = roster.remove_student(created.class_id, "s1")

    assert removed == "s1"
    assert roster.authenticate_student("s1", "next") is None
    assert roster.student(created.class_id, "s2").name == "乙"
    with pytest.raises(RosterError, match="学生不存在"):
        roster.student(created.class_id, "s1")


def test_deleting_a_class_removes_its_accounts_only():
    roster = Roster()
    first = roster.create_class("一班")
    second = roster.create_class("二班")
    roster.import_rows(first.class_id, ((2, "s1", "secret", "甲"),))
    roster.import_rows(second.class_id, ((2, "s2", "secret", "乙"),))

    removed = roster.delete_class(first.class_id)

    assert removed == ("s1",)
    assert roster.classes() == (second,)
    assert roster.authenticate_student("s2", "secret").name == "乙"
    with pytest.raises(RosterError, match="班级不存在"):
        roster.students(first.class_id)
