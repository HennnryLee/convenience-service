# 程序插装报告（教材 11.4）

- 被插装模块：`app/services/appointment_rules.py`
- 插装方式：`sys.settrace` 逐行回调（等价于在每行前插入计数器语句）
- 场景数：9（覆盖 7 个判定的真/假分支）
- 可执行语句数：27，被执行：27，未执行：0
- 语句插装覆盖率：100.0%

## 逐行执行次数（探测器读数）

| 行号 | 语句 | 执行次数 |
| --- | --- | --- |
| 158 | `require(isinstance(context, AppointmentContext), "context 必须是 AppointmentContext")` | 10 |
| 159 | `require(appointment_date is None or isinstance(appointment_date, date), "appointment_date 必须是 date 或 None")` | 10 |
| 160 | `require(isinstance(max_days_ahead, int) and max_days_ahead >= 1, "max_days_ahead 必须是正整数")` | 10 |
| 161 | `slots_snapshot = tuple(TIME_SLOTS)` | 10 |
| 163 | `errors = []` | 10 |
| 164 | `if today is None:` | 10 |
| 165 | `today = date.today()` | 1 |
| 166 | `require(isinstance(today, date), "today 必须是 date")` | 10 |
| 168 | `if not context.service_online:` | 10 |
| 169 | `errors.append("该服务已下架，暂不可预约。")` | 1 |
| 171 | `if appointment_date is None:` | 10 |
| 172 | `errors.append("请选择预约日期。")` | 1 |
| 173 | `ensure(isinstance(errors, list) and all(isinstance(e, str) and e for e in errors), "错误列表元素必须非空")` | 3 |
| 174 | `return errors` | 1 |
| 176 | `if appointment_date < today:` | 9 |
| 177 | `errors.append("不能预约过去的日期。")` | 1 |
| 178 | `elif (appointment_date - today).days > max_days_ahead:` | 8 |
| 179 | `errors.append(f"仅可预约未来 {max_days_ahead} 天内的服务。")` | 1 |
| 181 | `if not is_valid_slot(slot):` | 9 |
| 182 | `errors.append(f"预约时段无效，可选时段：{'、'.join(TIME_SLOTS)}。")` | 1 |
| 184 | `if context.has_duplicate:` | 9 |
| 185 | `errors.append("你已预约该时段，请勿重复提交。")` | 1 |
| 187 | `if remaining_capacity(context.capacity, context.used) <= 0:` | 9 |
| 188 | `errors.append("该时段预约名额已满，请选择其它时段。")` | 1 |
| 190 | `ensure(isinstance(errors, list) and all(isinstance(e, str) and e for e in errors), "错误列表元素必须非空")` | 24 |
| 191 | `invariant(tuple(TIME_SLOTS) == slots_snapshot, "时段表在校验过程中不得被修改")` | 9 |
| 192 | `return errors` | 9 |

**结论**：本场景集覆盖了模块内全部可执行语句，无未执行语句（死代码 0 处）。
