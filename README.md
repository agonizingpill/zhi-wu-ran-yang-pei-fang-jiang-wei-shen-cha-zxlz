# 栖色织研 · 织物染样配方降维审查

36 波段光谱降维、CIELAB 色差确认与复染配方冻结，面向栖色织研 24 人染整研发组。

上游为光谱仪导出的 `reflectance_20261117.csv`，调色师现在用纸样册和 Excel 比对；36 波段难比较、浓度尺度影响距离、超色差配方仍流向车间。系统接管配方—实测染样—复染签批环节，下游车间只接收主管放行配方。

## 启动

```sh
cp .env.example .env
docker compose up -d --build
# 启动自动 seed；也可人工重复执行（只插入缺少的自然键）
docker compose exec -T backend python -m scripts.seed_demo
```

前端 [localhost:18220](http://localhost:18220)，后端 [localhost:19220/docs](http://localhost:19220/docs)，数据库 17720。停止并删除演示数据：`docker compose down -v --remove-orphans`。

|账号|角色|权限|
|---|---|---|
|admin@qise.test|admin 主管|全部录入、计算、确认、最终签批|
|colorist@qise.test|colorist 调色师|配方/染样录入、PCA、试验与色差确认，不能最终批准|
|viewer@qise.test|viewer 观察员|十页与审计记录只读|

演示密码均为 `Dye2026!`。JWT 有效期 8 小时；所有变更通过后端鉴权。数据库密码与 JWT 默认密钥为本地演示配置。

## 业务模块

- 配方目录：三种染料浓度、唯一配方编号与冻结保护；冻结不能改浓度或追加染样。
- 染样登记：配方外键、唯一批号、36 波段 0–1 反射率、CIELAB 实测值。
- PCA 图谱与配对：Redis 队列交给 Python worker，返回 60 个实算坐标、解释方差与重构误差；建立同配方染样复染配对。
- 复染签批：草稿 → 调色师确认 → 主管批准；批准自动冻结关联配方。ΔE>3 的草稿确认后进入退回修色状态，不能批准。

`ΔE76 = sqrt((L1−L2)^2+(a1−a2)^2+(b1−b2)^2)`；门限 3 为模拟工艺规则，PCA 距离不能代替色差判定。PCA 对 36 维反射率用 StandardScaler，二维 PCA / full SVD / random_state=42；重构 MSE 在标准化空间计算。小于三张染样时计算失败。seed `random.Random(42)`，60 张样本、3 个配方。Redis 结果保存 24 小时，共享 artifacts 卷留存 JSON。

## 一天剧本

1. 08:30 调色师登录，检查 DY-021 靛蓝亚麻（A1.8%、B0.4%、C0.2%）。
2. 09:00 核对 `reflectance_20261117.csv` 与 REF-021（L48/a−2/b−25）。
3. 09:30 登记 SAMPLE-021（L48.7/a−1.5/b−24.5，ΔE≈0.995）。
4. 10:00 生成 60 张染样 PCA 图谱，检查解释方差与重构误差。
5. 10:30 建立 REF-021→SAMPLE-021 复染配对。
6. 11:00 以 SAMPLE-OFF（L62/a8/b−14）测试超限，确认后退回修色。
7. 14:00 调色师确认合格试验，主管批准，配方冻结。
8. 16:00 车间观察员查签批簿与审计账号，依据冻结配方安排复染。

## 工程与本地开发

Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL16 / Redis7 / scikit-learn1.6；前端原生 ES modules / HTML / CSS / Nginx1.27。

`backend/src/models.py` 定义领域模型；`schemas.py` 校验输入；`recipe_service.py` 承担领域规则和审计；`app.py` 路由及两道中间件；`atlas.py` 纯 Python ML；`worker.py` 消费队列、记录心跳；`backend/scripts/seed_demo.py` 幂等数据。首次启动 SQLAlchemy metadata 建表，本小型项目不含后续在线迁移工具。

前端 `src/api.js` API、`store.js` 状态、`utils.js` 格式与反馈、`components/common.js` 标题/状态/光谱/证据表、`pages/` 十个业务页面。角色与试验状态枚举分别位于 `backend/src/constants.py` 与 `frontend/src/constants.js`。

本地后端：创建 Python3.12 venv，安装 `backend/requirements.txt`，设置 DATABASE_URL/REDIS_URL 指向映射端口，进入 backend 运行 `uvicorn src.app:app --reload`；worker 同目录运行 `python -m src.worker`（本地 `/artifacts` 路径需有写权限）。本地前端可经现成 Nginx 容器开发，修改后 compose build frontend。

环境变量：COMPOSE_PROJECT_NAME 容器名前缀、FRONTEND_PORT/BACKEND_PORT/DB_PORT 宿主端口、JWT_SECRET 签名密钥、SEED_DEMO 自动 seed；NETWORK_SUBNET 可调整显式私有子网（默认10.221.21.0/24，规避本机默认地址池耗尽）。服务内部 DATABASE_URL、REDIS_URL 由 Compose 指定。五服务均有真实健康检查；db/redis/artifacts 三个命名卷。业务与浏览器验收在源码外 `test-artifacts/gb-1021/`。

## License

MIT，见 LICENSE。


## 业务扩展（2026-11-17）

新增两个独立业务模块，业务数据持久化到 PostgreSQL：

- **配方修订谱系**：冻结父配方复制成新子版本，保存父编号、名称与三染料浓度快照；修订理由必填。主管审核来源前，子版不能改浓度、追加染样或建立复染试验。审核后可独立调整子版，原版继续冻结。子版必须是新编号，拒绝重复子版本与循环关联。
- **生产缸次色差验收**：已批准复染试验才能下生产缸次，保存目标色样快照。登记生产 Lab 后由 Python 实算 ΔE76；超过3进入扣留，可修色后复测；合格后主管签放，放行后实测值冻结。观察员只读，调色师可登记但不能审核来源或签放生产。

新实体为 `RecipeRevision`（父子配方外键、来源快照、审核状态）与 `DyeBatch`（唯一缸号、批准试验外键、重量、Lab、色差、状态、签放人）。谱系为 `pending→approved`，生产为 `planned→hold/qualified→released`。生产扣留可重新测量；来源审核与生产签放均不重复执行。

新增接口：`GET/POST /revisions`、`POST /revisions/{id}/review`、`GET/POST /batches`、`PUT /batches/{id}/measurement`、`POST /batches/{id}/release`。五个后端业务文件位于 `backend/src/production_models.py`、`production_schemas.py`、`revision_service.py`、`batch_service.py`、`production_routes.py`；前端新页为 `pages/revisions.js` 和 `pages/batches.js`。

扩展 seed 新增 DY-PROD 冻结量产基准、PROD-REF/PROD-OK 两张实测染样、已批准量产试验和 DB-DEMO-001 待测缸次；全新库基础数据为3用户、4配方、62染样。连续seed只补缺项，保留人工编辑、修订谱系及缸次结果。本次没有更改旧表字段，自动建表为既有演示库补充两个新表；生产环境仍建议使用版本化迁移。

演示续篇：冻结原版→建立细支亚麻修订→主管审来源→调色师调整子版；从批准小样建立400kg生产缸→登记超色差实测并扣留→修色复测合格→主管签放。新的真实验收、4张1440×900截图与已知差异见 `test-artifacts/gb-1021/expansion/`。


## V3：染料称料、客户发样与色差补染

保留原配方、染样、PCA、复染签批、修订谱系和生产验收六页，新加三页，合计九个业务页面。

- **染料库存称料**：`DyeLot`按A/B/C组分记录唯一批号、可用kg、有效期和隔离状态。`DyeIssue`关联生产缸与实际来源批次，每缸每组分唯一，保留配方浓度快照和称料人。服务器计算“浓度%×生产kg÷100”，先锁缸次、按ID排序锁三个批次，全部校验后整单扣减。过期、隔离、不足或组分不匹配均不扣任一项；重复及并发领料只能成功一次。新生产签放必须A/B/C凭据齐全；历史已签放不追加领料或补扣。
- **客户色样签收**：`ColorDispatch`每个已签放缸只能发样一次，保存运单、客户、实测Lab、原目标、配方、生产kg和签放人快照。发样→实际收件人签收→接受或色差争议；未签收、跨缸结论和重复结论被拒绝。客户原争议记录冻结，后续补染另单处理。
- **色差客诉补染**：`ShadeComplaint`仅关联已签收且争议的发样单，申请kg不得超过原缸。主管裁定补染或驳回；补染须新的、未用于其他生产缸的approved trial，且新目标色与原客户目标ΔE≤3，系统按申请kg创建唯一关联新缸。新缸正常称料、实测、主管签放后，主管才可关闭；原缸、其他缸、未放行新缸或重复关闭都拒绝。

角色：调色师可入库、称料、发样、记录客户签收/反馈、提出客诉和建立已批准补染新缸；主管另外负责隔离/解除染料、补染裁定、生产签放及关闭客诉；观察员九页只读。客户反馈由内部岗位依据实际交接记录，不新增外部客户登录或对外消息。

接口：`GET/POST /dye-lots`、`PUT /dye-lots/{id}/state`、`GET/POST /dye-issues`；`GET/POST /color-dispatches`及`POST /{id}/receive`、`POST /{id}/conclusion`；`GET/POST /shade-complaints`及`POST /{id}/decision`、`POST /{id}/remake`、`POST /{id}/close`。主管专属动作由JWT后端依赖保护，非仅前端禁用。

新增代码按职责分为`fulfillment_models.py`、`fulfillment_schemas.py`、`fulfillment_routes.py`与`stock_service.py`、`dispatch_service.py`、`complaint_service.py`；前端新增`pages/stock.js`、`pages/dispatches.js`、`pages/complaints.js`。原batch_service在新建时保存配方快照、签放时核称料，补染新缸与客诉关联一次事务提交。四个新表自动补建，没有旧表列变更，保留既有released状态及旧格式目标快照。

Seed再补5个染料批次：A80kg、B40kg、C20kg可用，C隔离5kg、B已过期5kg作为拒领剧本；重复seed不补满消耗、不清除客诉、不覆盖人工修改。基础用户3、配方4、染样62仍保持；新签收与客诉从实际生产动作产生。

续篇剧本：为200kg靛蓝缸称A3.6/B0.8/C0.4kg→色差实测合格并签放→禾里服装收样，林工签收后记录标准光源色差争议→申请100kg补染→主管批准→新试验关联新缸，称A1.6/B0.4/C0.2kg→新缸正常实测签放→主管关闭客诉。新库存、客户与补染证据独立归档`test-artifacts/gb-1021/v3/`。

限制：库存仅染料批次扣料，不包含采购、货位、退库与盘点；客户运单和签收为本地人工凭据，未调用物流或客户门户。补染不出款、不改旧发样结论，不含合同索赔金额。Lab、光谱和工艺门限仍为模拟业务，需真实仪器及客户容差规范校准。


## V4：排产换色判定与清洗凭据

新增第十页“排产换色判定”。深色缸接浅色缸容易串色，系统用同机历次免洗换色的前后配方与首测色差预测免洗超差风险，证据不足一律要求清洗。

- **历史换色证据池**：`ColorChangeRecord` 保存染机、前后配方浓度快照、是否免洗与首测 ΔE；人工登记与完工自动生成两条来源。只有免洗记录进入证据池，清洗记录仅留档。
- **换色判定**：排产/插单即按当前前缸自动判定。同机免洗记录中前后配方浓度距离（A/B/C 欧氏距离 ≤0.8）均匹配的 ≥2 条且首测 ΔE 全部 ≤3，判“免洗可行”并按染机留出首测检验；证据不足或历史超差，判“要求清洗”。判定依据（证据明细、配方距离、浓度合计、判定时间）整份存入缸次 `judgment` 供回看。
- **开染规则**：仅本机队列最前的待排缸可开染，且上缸须已完工；开染以同机实际完工的上一缸为准核对判定。要求清洗的缸必须持有有效清洗凭据（主管确认）才能开染，凭据在开染事务内核销。
- **改排与插单**：凭据只对登记时的前后两缸有效；插单或改排改变相邻关系，受影响凭据同事务失效，相关缸次判定过期，重算前拦截开染。改排与开染并发时以缸次行锁定序：先开染的缸留在原机（改排拒绝），先改排则按新顺序重算判定后才能开染。
- **幂等开染**：开染请求携带 `request_key`，写入中断后用同一 key 重试直接返回原结果，不重复核销清洗凭据；换 key 重复开染拒绝。
- **回看**：排产、判定、改排、确认清洗、凭据失效、开染、拦截、完工全部写入 `schedule_events`，页面按缸次展开判定依据与拦截原因。

新实体：`DyeMachine`、`ScheduleSlot`（机台队列、配方快照、判定 JSON、检验预留、开染幂等键）、`ColorChangeRecord`、`CleaningVoucher`（前后缸对、有效/已核销/已失效）、`ScheduleEvent`。代码位于 `schedule_models.py`、`schedule_schemas.py`、`schedule_service.py`、`schedule_routes.py`，前端新页 `pages/schedule.js`。

接口：`GET /schedule/machines|slots|history|vouchers|events`，`POST /schedule/slots`、`POST /schedule/slots/{id}/reschedule|rejudge|start|complete`，`POST /schedule/history`，`POST /schedule/vouchers`（主管）。完工登记首测 ΔE 自动生成换色记录回流证据池。

Seed 新增 M1/M2/M3 三台染机、5 条历史换色（含免洗合格、免洗超差与已清洗样本）与 M1 队列：Q-1101 已完工、Q-1102 免洗可行留出检验、Q-1103 证据不足要求清洗；重复 seed 只补缺项。

演示剧本：Q-1102 免洗开染（同 key 重试安全返回）→完工生成免洗记录→Q-1103 缺凭据被拦截→主管确认清洗→插单 Q-INS4 凭据即失效、判定过期→重算前开染被拦→插单缸洗完开工→Q-1103 重算、重新确认清洗、凭据开染→登记两条 DY-023→DY-021 免洗记录后新排缸次判定翻转为免洗。

限制：判定规则为模拟工艺门限（容差 0.8、证据 2 条、ΔE 3），未接入真实机台状态与检验仪器；队列为单机单缸模型，不含并行缸与计划排程优化。
