#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


DEFAULT_TURNS = [
    "我希望创建一个态势分析系统。这个态势分析系统里面要有态势的展示，要有一系列态势分析工具，比如地理信息分析工具、通视量算、坡度分析，还有部署分析系统。但是当前用户、使用模式我都没有想清楚，希望你来一块帮我想清楚。",
    "软件定位先按面向科研分析和业务验证的态势分析软件考虑，不作为正式指挥决策系统。第一阶段重点是把态势对象、地图图层、空间分析工具和成果输出做成闭环。",
    "主要用户包括科研分析人员、参谋分析员、业务专家、数据管理员和系统管理员。科研分析人员和参谋分析员创建工程、加载数据、执行分析；业务专家复核结果；数据管理员维护基础地理数据和专题数据；系统管理员负责账号、权限、日志、模板和默认参数。",
    "典型场景包括任务前区域研判、任务中态势变化辅助分析、部署方案可行性检查、专题图件和报告输出。主流程是新建态势工程，加载底图、DEM、矢量、栅格和业务对象，选择分析工具，输入对象或参数，执行计算，查看结果，导出图件、表格和简要报告，再由业务专家复核。",
    "接口需求方面，第一阶段以文件导入导出和内网数据加载为主。输入接口包括底图服务或底图文件、DEM/DSM地形数据、矢量图层、栅格影像、任务区域、禁限区、部署点位、传感器或观察点位、人工标注文件。输出接口包括态势工程文件、专题图件、分析结果图层、结果参数表、简化研判报告和审计记录导出。暂不做实时数据总线和跨单位在线协同接口。",
    "功能需求要按需求功能模块拆。第一组是态势工程管理：新建、打开、保存、另存为、关闭工程，记录工程坐标系、图层清单、标绘对象、分析参数、结果图层和版本说明。第二组是地图与态势展示：支持缩放、平移、图层开关、透明度、对象选中、属性查看、态势对象高亮、时间戳显示和结果叠加。",
    "第三组功能是标绘与对象管理：支持点、线、面、文字、部署点、观察点、目标点、任务区域、禁限区、影响范围等对象创建、编辑、删除、属性维护和样式设置。第四组功能是基础量算：支持距离、面积、坐标、高程读取、坡度坡向、高程剖面等分析，输出数值、图形和参数说明。",
    "第五组功能是通视与可视域分析：支持选择观察点、目标点、观察高度、目标高度、地形数据和分析半径，计算两点通视、多点通视或可视域，输出可视/不可视结论、遮挡位置、剖面图和结果图层。第六组功能是部署分析：支持覆盖范围、冲突检查、影响范围、可行性辅助判断，重点提示风险和约束，不做自动最优推荐。",
    "第七组功能是结果管理与成果输出：分析结果可以保存为结果图层、结果表、参数记录和说明片段；支持按工程、任务、时间、工具类型查询；支持导出PNG或PDF专题图、CSV或XLSX结果表、Markdown或PDF简要报告；报告需要带数据来源、时间、算法参数、适用限制和复核意见。",
    "性能需求方面，地图基本浏览在普通数据规模下交互响应目标小于2秒，常规属性查询和图层开关小于2秒，普通量算和坐标查询小于5秒，坡度坡向、高程剖面、两点通视等常规分析小于30秒，大范围可视域和部署影响分析允许1到3分钟并显示任务进度。第一阶段按30个并发用户、5个并发复杂分析任务做目标，超出时排队或提示。",
    "安装和操作要求方面，第一阶段按内网部署考虑，提供服务器端部署包、前端访问入口、初始化脚本、默认管理员账号创建、基础图层目录配置、算法参数默认值配置、日志目录配置和备份目录配置。普通分析员不需要写配置文件，应通过界面创建工程、加载数据、选择工具、调整参数和导出成果。管理员可以维护用户、角色、默认参数、模板、字典和系统日志。",
    "运行环境硬件需求方面，建议区分服务器和客户端。服务器至少需要能够支撑地形、影像、矢量和工程文件存储，配置要预留DEM和影像索引空间；客户端应支持主流办公终端和较大屏幕显示，地图浏览和常规二维分析不强制专用显卡，大范围栅格分析和可视域分析可由服务器执行。具体CPU、内存、存储和网络带宽作为待确认指标。",
    "运行环境软件需求方面，服务器操作系统优先考虑国产化Linux或通用Linux，数据库可选PostgreSQL/PostGIS或同等空间数据库，文件存储用于工程包、导出图件和报告；前端支持主流现代浏览器；地图能力依赖二维WebGIS引擎、坐标转换库、栅格处理库和分析算法库。第三方GIS、地图服务、商用库授权和离线瓦片使用范围需要在后续确认。",
    "数据与信息要求方面，输入数据包括底图、DEM/DSM、遥感影像、矢量要素、业务对象、部署点位、任务区域、禁限区、观察点、目标点、人工标注和分析参数。所有输入数据要记录来源、坐标系、时间、版本和质量说明。坐标系不一致时应提示转换或阻断，DEM缺块时要标注影响范围，过期数据应提示用户确认。",
    "质量、安全和约束方面，系统结果只作为辅助研判，不作为正式决策依据，不承诺测绘级或工程级精度。系统需要角色权限、数据访问控制、操作审计、结果可追溯、导出水印或密级标注。关键操作包括登录、数据导入、参数修改、执行分析、保存工程、删除结果、导出成果、权限调整，都应记录日志。",
    "异常补偿方面，至少处理数据缺失、坐标系不一致、计算失败、保存失败、权限不足、导出失败、实时数据中断、DEM缺块、参数不合法、任务超时和外部服务不可用。异常发生时要给出原因、影响范围、可恢复动作和是否需要人工复核。不能静默忽略高风险异常，也不能自动把低质量结果写成可信结论。",
    "验收任务链包括：一，创建态势工程并加载底图、DEM、矢量和业务对象；二，完成地图浏览、图层控制和对象标绘；三，完成距离面积量算、坡度坡向、高程剖面、通视分析和部署影响分析；四，模拟数据缺失和坐标系不一致异常；五，导出专题图、结果表和简要报告；六，检查权限、日志和结果追溯。",
    "验收准则要覆盖功能、接口、性能、安装操作、运行环境、数据质量、安全权限和输出物。功能通过标准是每个需求功能模块均能按输入、处理、输出闭环执行；接口通过标准是导入导出格式可读、错误可提示；性能通过标准是常规操作达到约定响应；安装通过标准是管理员能完成初始化；安全通过标准是越权访问被阻断并记录日志。",
    "回看一下当前工程需求哪些已经闭合，哪些还缺，尤其看接口需求、功能需求、性能需求、安装操作要求、硬件需求、软件需求是否足够支撑成稿。",
    "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。工程需求章节要尽量写得丰富，功能需求按需求功能模块展开，不要只列功能名称。",
]

DYNAMIC_INITIAL_INPUT = (
    "我希望创建一个态势分析系统。这个态势分析系统里面要有态势的展示，要有一系列态势分析工具，"
    "比如地理信息分析工具、通视量算、坡度分析，还有部署分析系统。"
    "但是当前用户、使用模式我都没有想清楚，希望你来一块帮我想清楚。"
)

DYNAMIC_EXAMINER_FACTS = [
    {
        "domain": "user_roles",
        "triggers": ["用户", "角色", "谁用", "使用者", "人员", "权限", "专家"],
        "action": "answer_question",
        "text": "用户角色按科研分析人员、参谋分析员、业务专家、数据管理员和系统管理员划分。科研分析人员和参谋分析员创建态势工程、加载数据、执行空间分析和导出成果；业务专家复核结果并给出意见；数据管理员维护基础地理数据、专题图层、DEM和影像；系统管理员负责账号、角色权限、日志审计、模板、默认参数和运行配置。普通查看者只查看态势、结果摘要和报告，不允许修改工程和参数。",
    },
    {
        "domain": "software_positioning",
        "triggers": ["定位", "目标", "价值", "解决", "建设", "目的", "范围", "领域", "应用", "名称"],
        "action": "answer_question",
        "text": "软件定位为面向科研分析和业务验证的态势分析软件，兼具态势展示、地图图层管理、空间分析计算和成果输出能力。第一阶段目标是形成从数据加载、态势展示、分析计算、结果复核到成果导出的闭环，不作为正式指挥决策系统，不提供自动决策推荐、火力分配、最优部署求解或跨单位实时协同指挥。",
    },
    {
        "domain": "workflow",
        "triggers": ["流程", "怎么用", "场景", "步骤", "业务过程", "使用模式"],
        "action": "answer_question",
        "text": "主流程按任务前区域研判、任务中态势变化辅助分析、部署方案可行性检查三类场景组织。用户先新建工程并选择坐标系，加载底图、DEM、影像、矢量、任务区域、禁限区和部署点位，创建或编辑标绘对象；随后选择量算、坡度坡向、高程剖面、通视或部署分析工具，输入观察点、目标点、分析半径、时间、地形数据和其他参数；系统执行计算并生成图层、表格、剖面图或风险提示；最后用户保存工程、导出专题图件和简要报告，业务专家复核后形成记录。",
    },
    {
        "domain": "core_functions",
        "triggers": ["功能", "工具", "能力", "模块", "态势", "展示", "编辑"],
        "action": "answer_question",
        "text": "功能需求按需求功能模块拆分：一是态势工程管理，支持工程新建、打开、保存、另存为、关闭、工程坐标系、图层清单、标绘对象、分析参数、结果图层和版本说明管理；二是地图与态势展示，支持缩放、平移、图层开关、透明度、对象选中、属性查看、时间戳显示、结果叠加和状态高亮；三是标绘与对象管理，支持点、线、面、文字、观察点、目标点、部署点、任务区域、禁限区和影响范围编辑；四是基础量算，支持距离、面积、坐标、高程、坡度坡向和高程剖面；五是通视和可视域分析；六是部署覆盖、冲突和影响范围分析；七是结果管理、复核和成果输出。",
    },
    {
        "domain": "function_module_details",
        "triggers": ["功能模块", "输入", "处理", "输出", "验收要点", "模块细化", "功能细化", "详细功能"],
        "action": "answer_question",
        "text": "功能模块细化如下：态势工程管理模块由科研分析人员和参谋分析员使用，输入工程名称、坐标系、底图目录、工程说明、图层清单和任务编号，系统创建工程结构、保存图层引用、标绘对象、分析参数、结果图层和版本说明，输出可再次打开的态势工程包；异常包括坐标系缺失、工程目录不可写、版本冲突和保存失败，验收时要求工程关闭后重新打开仍能恢复图层、对象、参数和结果。地图与态势展示模块输入底图、影像、矢量、态势对象和结果图层，系统提供缩放、平移、图层开关、透明度、对象选中、属性查看、时间戳显示、状态高亮和结果叠加，输出当前态势视图和可截图的地图状态，验收时要求普通图层浏览稳定且对象属性可追溯。标绘与对象管理模块输入点线面文字、观察点、目标点、部署点、任务区域、禁限区和影响范围，系统支持创建、编辑、删除、属性维护、样式设置、批量选择和撤销重做，输出规范化标绘对象和属性表。",
    },
    {
        "domain": "analysis_module_details",
        "triggers": ["通视", "可视域", "量算", "坡度", "部署分析", "分析工具", "空间分析"],
        "action": "answer_question",
        "text": "空间分析模块进一步细化：基础量算模块输入点、线、面、坐标、DEM和地图比例尺，输出距离、面积、坐标、高程、坡度坡向和高程剖面结果，要求结果带单位、坐标系、输入对象编号和计算时间；通视与可视域分析模块输入观察点、目标点、观察高度、目标高度、分析半径、地形数据和遮挡参数，系统计算两点通视、多点通视和可视域范围，输出可视或不可视结论、遮挡位置、剖面图、可视域栅格或矢量结果图层，异常时提示DEM缺块、半径过大、点位无高程或参数不合法；部署分析模块输入部署点、任务区域、禁限区、影响半径、覆盖规则和冲突规则，系统计算覆盖范围、冲突位置、影响范围和可行性辅助提示，输出风险清单、冲突对象、影响范围图层和说明片段，不输出自动最优部署方案。",
    },
    {
        "domain": "result_management_details",
        "triggers": ["结果管理", "成果输出", "报告", "复核", "归档", "专题图"],
        "action": "answer_question",
        "text": "结果管理与成果输出模块要求分析结果保存为结果图层、结果表、参数记录、剖面图、风险清单和说明片段；支持按工程、任务、时间、工具类型、操作者和复核状态查询；支持对结果执行显示、隐藏、重命名、复制、删除、锁定、复核标记和版本对比；导出成果包括PNG或PDF专题图、CSV或XLSX结果表、Markdown或PDF简要报告、GeoJSON或GeoPackage候选结果图层和审计记录。报告需要包含任务背景、输入数据来源、坐标系、参数、算法或规则说明、结果摘要、风险提示、适用限制、复核意见和导出时间。业务专家只能复核和批注意见，不能修改原始参数和历史结果。",
    },
    {
        "domain": "interface_requirements",
        "triggers": ["接口", "导入", "导出", "文件", "内网", "外部系统", "交换"],
        "action": "answer_question",
        "text": "接口需求第一阶段以文件导入导出和内网数据加载为主。输入接口包括底图服务或底图文件、DEM/DSM地形数据、遥感影像、矢量图层、任务区域、禁限区、部署点位、观察点、目标点和人工标注文件；支持GeoJSON、Shapefile、GeoPackage、GeoTIFF、CSV、XLSX和工程包等候选格式，具体格式以后确认。输出接口包括态势工程包、专题图件、分析结果图层、结果参数表、审计记录和简化研判报告。接口失败时要提示失败原因，保留重新导入、重新导出、手工修正和人工复核入口。",
    },
    {
        "domain": "data_interfaces",
        "triggers": ["数据", "接口", "导入", "导出", "图层", "底图", "DEM", "矢量", "栅格"],
        "action": "answer_question",
        "text": "数据与信息要求包括输入数据、输出数据和追溯信息。输入数据包括底图、DEM/DSM、遥感影像、矢量要素、业务对象、部署点位、任务区域、禁限区、观察点、目标点、人工标注和分析参数；每类输入数据都要记录来源、坐标系、时间、版本、精度和质量说明。输出数据包括态势工程文件、专题图图片、分析结果图层、结果参数表、剖面图、风险清单、简化报告和任务记录。所有分析结果应记录输入数据、算法参数、操作者、执行时间和适用限制。",
    },
    {
        "domain": "scope_boundary",
        "triggers": ["边界", "不做", "排除", "限制", "范围", "协同", "决策"],
        "action": "answer_question",
        "text": "第一阶段不做实时多源情报接入，不做自动决策推荐，不承诺高精度测绘级或工程级计算，也不做多单位在线协同指挥。分析结果只能作为辅助判断。",
    },
    {
        "domain": "quality_constraints",
        "triggers": ["非功能", "性能", "安全", "可靠", "部署", "精度", "质量"],
        "action": "answer_question",
        "text": "性能需求按场景量化：地图浏览、缩放、平移、对象选中和图层开关在普通数据规模下目标小于2秒；属性查询和常规坐标读取小于2秒；距离面积量算、坐标查询小于5秒；坡度坡向、高程剖面和两点通视小于30秒；大范围可视域和部署影响分析允许1到3分钟并显示进度。第一阶段按30个并发用户和5个并发复杂分析任务作为暂定目标，超出时任务排队或提示。安全方面需要角色权限、数据访问控制、操作审计、结果可追溯、导出水印或密级标注。精度方面只承诺辅助研判级，不承诺测绘级或工程级。",
    },
    {
        "domain": "installation_operation",
        "triggers": ["安装", "操作", "初始化", "配置", "部署包", "运维", "升级", "备份"],
        "action": "answer_question",
        "text": "安装和操作要求包括服务器端部署包、前端访问入口、初始化脚本、默认管理员账号、基础图层目录配置、算法参数默认值配置、日志目录配置、备份目录配置和导出目录配置。管理员应能在界面中维护用户、角色、默认参数、模板、字典、系统日志和数据目录。普通分析员不应直接编辑配置文件，应通过界面完成工程创建、数据加载、工具选择、参数调整、结果查看、保存和导出。升级时要保留工程文件、用户权限、参数配置、日志和历史结果。",
    },
    {
        "domain": "runtime_environment",
        "triggers": ["硬件", "软件", "服务器", "客户端", "数据库", "浏览器", "操作系统", "GIS", "运行环境"],
        "action": "answer_question",
        "text": "运行环境要求分硬件需求和软件需求。硬件方面，服务器要支撑地形、影像、矢量、工程文件、结果图层和报告存储，并预留DEM和影像索引空间；客户端按普通办公终端和较大屏幕显示考虑，二维地图浏览不强制专用显卡，大范围栅格分析和可视域分析由服务器执行；具体CPU、内存、存储和网络带宽作为待确认指标。软件方面，服务器操作系统优先考虑国产化Linux或通用Linux，空间数据库可选PostgreSQL/PostGIS或同等能力数据库，前端支持主流现代浏览器，地图能力依赖二维WebGIS引擎、坐标转换库、栅格处理库和分析算法库，第三方GIS、离线瓦片和商用库授权后续确认。",
    },
    {
        "domain": "exceptions_acceptance",
        "triggers": ["异常", "补偿", "验收", "测试", "失败", "错误", "准则"],
        "action": "answer_question",
        "text": "业务规则和异常补偿至少包括数据缺失、坐标系不一致、计算失败、保存失败、权限不足、导出失败、实时数据中断、DEM缺块、参数不合法、任务超时和外部服务不可用。异常发生时要给出原因、影响范围、可恢复动作和是否需要人工复核。验收任务链至少覆盖工程创建、数据加载、地图浏览、图层控制、对象标绘、距离面积量算、坡度坡向、高程剖面、通视分析、部署影响分析、异常提示、专题图导出、报告生成、权限校验、日志审计和历史记录追溯。",
    },
    {
        "domain": "acceptance_details",
        "triggers": ["通过标准", "验收场景", "验收准则", "测试用例", "验收链路"],
        "action": "answer_question",
        "text": "验收细化为六条任务链：第一条是安装初始化链路，管理员在内网环境完成部署、初始化账号、配置基础图层目录、配置默认算法参数、查看日志目录和备份目录；通过标准是普通用户能登录并看到授权菜单，管理员能维护用户和参数。第二条是工程创建链路，分析员新建工程、加载底图、DEM、影像、矢量和业务对象，保存后重新打开；通过标准是图层、对象、坐标系、参数和版本说明均恢复。第三条是空间分析链路，完成距离面积量算、坡度坡向、高程剖面、通视分析和部署影响分析；通过标准是结果带单位、参数、来源和适用限制。第四条是异常链路，模拟坐标系不一致、DEM缺块、权限不足、保存失败和导出失败；通过标准是系统提示原因、影响范围和可恢复动作。第五条是成果输出链路，导出专题图、结果表和简要报告；通过标准是输出物可打开、内容完整、带水印或标识、可追溯。第六条是安全审计链路，检查登录、数据导入、参数修改、分析执行、保存、删除、导出和权限调整日志；通过标准是越权被阻断且关键操作可追溯。",
    },
]

DYNAMIC_CORRECTIONS = [
    {
        "triggers": ["自动决策", "自动推荐", "指挥决策", "正式指挥", "处置"],
        "action": "light_correction",
        "text": "这里你理解得有点重了，第一阶段只做科研分析和业务验证中的辅助分析，不做自动决策推荐，也不把结果表述为正式指挥结论。",
    },
    {
        "triggers": ["通用模板", "模板"],
        "action": "light_correction",
        "text": "这里要区分模板和当前项目事实。态势展示、空间分析、通视这些是态势分析系统样例项目的业务功能，不是通用需求规格模板本身。",
    },
]

DYNAMIC_REVIEW_INPUT = "你先回看一下：目前哪些关键决策已经闭合，哪些还没有闭合？先不要急着完整定稿。"
DYNAMIC_CONVERGENCE_INPUT = "强制停止追问，基于当前所有已确认信息输出完整需求规格说明草案，并列出仍需后续确认事项。"


def post_json(base_url: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.post(f"{base_url.rstrip('/')}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def post_json_with_retry(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    timeout: float,
    *,
    retries: int = 1,
    retry_delay_seconds: float = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return post_json(base_url, path, payload, timeout)
        except Exception as exc:  # noqa: BLE001 - probe runner preserves transient service failures.
            last_error = exc
            if attempt >= retries:
                break
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in {502, 503, 504}:
                break
            time.sleep(retry_delay_seconds)
    if last_error is not None:
        raise last_error
    raise RuntimeError("post_json_with_retry failed without captured exception")


def get_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.get(f"{base_url.rstrip('/')}{path}")
        response.raise_for_status()
        return response.json()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def jsonl_append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def http_error_payload(exc: httpx.HTTPStatusError) -> dict[str, Any]:
    return {
        "http_status": exc.response.status_code,
        "http_reason": exc.response.reason_phrase,
        "response_body": exc.response.text,
    }


def count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def count_active_open_questions(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    return len(
        [
            item
            for item in value
            if not isinstance(item, dict) or str(item.get("status") or "open").strip() == "open"
        ]
    )


def short_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").replace("\r\n", "\n").strip()
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def working_document_block_count(working_document: dict[str, Any]) -> int:
    for key in ("blocks", "revision_fragments", "sections"):
        value = working_document.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def working_document_text_chars(working_document: dict[str, Any]) -> int:
    blocks = working_document.get("blocks")
    if not isinstance(blocks, list):
        return 0
    return sum(len(str(block.get("text") or "")) for block in blocks if isinstance(block, dict))


def normalize_text_for_match(value: Any) -> str:
    return str(value or "").lower()


def latest_assistant_message(session: dict[str, Any]) -> str:
    messages = list(session.get("messages") or [])
    assistant_messages = [dict(item) for item in messages if dict(item).get("role") == "assistant"]
    return str(assistant_messages[-1].get("content") or "") if assistant_messages else ""


def should_stop_dynamic_probe_after_turn(session: dict[str, Any]) -> bool:
    next_interaction = dict(session.get("next_interaction") or {})
    interaction_type = str(next_interaction.get("type") or "").strip()
    return interaction_type in {"deliverable", "draft_delivery", "draft_with_gaps"}


def option_prefix(options: list[Any], *, fact_text: str) -> str:
    if not options:
        return ""
    normalized_fact = normalize_text_for_match(fact_text)
    for option in options:
        item = dict(option) if isinstance(option, dict) else {}
        label = str(item.get("label") or "").strip()
        key = str(item.get("key") or "A").strip() or "A"
        if label and label.lower() in normalized_fact:
            return f"{key}，我倾向于{label}。"
    return "不完全是这些选项。"


def choose_dynamic_examiner_input(
    *,
    turn_index: int,
    max_turns: int,
    last_session: dict[str, Any] | None,
    used_domains: set[str],
    recent_questions: list[str],
) -> dict[str, str]:
    if turn_index == 1 or not last_session:
        return {
            "user_input": DYNAMIC_INITIAL_INPUT,
            "examiner_action": "initial_intent",
            "examiner_reason": "首轮只输入基准起始描述。",
            "released_domain": "initial_intent",
        }
    if turn_index == max_turns:
        return {
            "user_input": DYNAMIC_CONVERGENCE_INPUT,
            "examiner_action": "convergence_request",
            "examiner_reason": "达到动态测试轮次上限，要求停止追问并输出带待确认事项的草案。",
            "released_domain": "convergence",
        }

    next_interaction = dict(last_session.get("next_interaction") or {})
    question = str(next_interaction.get("prompt") or latest_assistant_message(last_session))
    question_text = normalize_text_for_match(question)
    options = list(next_interaction.get("options") or [])

    if "scope_boundary" not in used_domains and any(
        trigger in question_text
        for trigger in [
            "不做哪些范围",
            "能力只做辅助分析",
            "第一阶段",
            "全部纳入第一阶段",
            "后续阶段再引入",
            "不纳入范围",
        ]
    ):
        fact = next(item for item in DYNAMIC_EXAMINER_FACTS if item["domain"] == "scope_boundary")
        prefix = option_prefix(options, fact_text=str(fact["text"]))
        user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
        return {
            "user_input": user_input,
            "examiner_action": "option_answer_with_supplement" if prefix else fact["action"],
            "examiner_reason": "组织器询问第一阶段范围、排除范围或辅助分析边界，优先释放 scope_boundary 事实。",
            "released_domain": "scope_boundary",
        }

    for fact in DYNAMIC_EXAMINER_FACTS:
        if fact["domain"] in used_domains:
            continue
        if any(trigger.lower() in question_text for trigger in fact["triggers"]):
            prefix = option_prefix(options, fact_text=str(fact["text"]))
            user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
            return {
                "user_input": user_input,
                "examiner_action": "option_answer_with_supplement" if prefix else fact["action"],
                "examiner_reason": f"按组织器当前问题释放 {fact['domain']} 主题事实。",
                "released_domain": fact["domain"],
            }

    for correction in DYNAMIC_CORRECTIONS:
        if any(trigger.lower() in question_text for trigger in correction["triggers"]):
            return {
                "user_input": correction["text"],
                "examiner_action": correction["action"],
                "examiner_reason": f"组织器输出触发纠偏关键词：{', '.join(correction['triggers'])}",
                "released_domain": "correction",
            }

    if len(recent_questions) >= 2 and len({item.strip() for item in recent_questions[-2:] if item.strip()}) == 1:
        for fact in DYNAMIC_EXAMINER_FACTS:
            if fact["domain"] not in used_domains:
                return {
                    "user_input": fact["text"],
                    "examiner_action": "small_guidance",
                    "examiner_reason": "组织器连续重复追问，按手册释放一个具体主题例子观察其归纳能力。",
                    "released_domain": fact["domain"],
                }

    if "review" in used_domains:
        return {
            "user_input": DYNAMIC_CONVERGENCE_INPUT,
            "examiner_action": "convergence_request",
            "examiner_reason": "已执行过回看请求，避免重复回看污染测试，转入收束交付验证。",
            "released_domain": "convergence",
        }

    if turn_index >= max_turns - 2:
        return {
            "user_input": DYNAMIC_REVIEW_INPUT,
            "examiner_action": "review_request",
            "examiner_reason": "接近轮次上限，要求先回看闭合与未闭合事项。",
            "released_domain": "review",
        }

    for fact in DYNAMIC_EXAMINER_FACTS:
        if fact["domain"] not in used_domains:
            prefix = option_prefix(options, fact_text=str(fact["text"]))
            user_input = f"{prefix}{fact['text']}" if prefix else fact["text"]
            return {
                "user_input": user_input,
                "examiner_action": "small_supplement",
                "examiner_reason": f"当前问题未命中特定主题，按信息释放限额补充 {fact['domain']}。",
                "released_domain": fact["domain"],
            }

    return {
        "user_input": DYNAMIC_REVIEW_INPUT,
        "examiner_action": "review_request",
        "examiner_reason": "事实池已释放完毕，要求组织器回看当前闭合状态。",
        "released_domain": "review",
    }


def extract_turn_metrics(
    *,
    orchestrator_id: str,
    turn_index: int,
    elapsed_seconds: float,
    user_input: str,
    response_payload: dict[str, Any],
    previous_provider_log_count: int,
    examiner_action: str = "",
    examiner_reason: str = "",
    released_domain: str = "",
) -> dict[str, Any]:
    session = dict(response_payload.get("session") or {})
    turn = dict(response_payload.get("turn") or {})
    decision_state = dict(session.get("decision_state") or {})
    working_document = dict(session.get("working_document") or {})
    messages = list(session.get("messages") or [])
    provider_logs = list(session.get("provider_logs") or [])
    spec_execution = dict(turn.get("spec_execution") or {})
    next_interaction = dict(turn.get("next_interaction") or {})
    post_update_review = dict(turn.get("post_update_review") or {})
    review_result = dict(turn.get("review_after_apply_result") or {})
    stage_audits = list(turn.get("stage_audits") or [])
    document_patch = list(spec_execution.get("document_patch") or session.get("document_patch") or [])
    assistant_message = spec_execution.get("assistant_message")
    if not assistant_message and messages:
        assistant_messages = [item for item in messages if dict(item).get("role") == "assistant"]
        assistant_message = dict(assistant_messages[-1]).get("content") if assistant_messages else ""

    return {
        "orchestrator_id": orchestrator_id,
        "turn_index": turn_index,
        "turn_id": turn.get("turn_id"),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": "ok",
        "user_input": short_text(user_input, 500),
        "examiner_action": examiner_action,
        "examiner_reason": short_text(examiner_reason, 500),
        "released_domain": released_domain,
        "assistant_message": short_text(assistant_message, 1200),
        "assistant_message_chars": len(str(assistant_message or "")),
        "next_question": short_text(next_interaction.get("prompt"), 800),
        "quick_options_count": count_list(next_interaction.get("options")),
        "confirmed_facts_count": count_list(session.get("confirmed_facts")),
        "session_open_questions_count": count_list(session.get("open_questions")),
        "decision_state_confirmed_facts_count": count_list(decision_state.get("confirmed_facts")),
        "decision_state_confirmed_decisions_count": count_list(decision_state.get("confirmed_decisions")),
        "decision_state_tentative_assumptions_count": count_list(decision_state.get("tentative_assumptions")),
        "decision_state_open_questions_count": count_list(decision_state.get("open_questions")),
        "decision_state_rejected_directions_count": count_list(decision_state.get("rejected_directions")),
        "decision_state_chapter_projections_count": count_list(decision_state.get("chapter_projections")),
        "document_patch_count": len(document_patch),
        "document_patch_chars": sum(len(str(item.get("content") or "")) for item in document_patch if isinstance(item, dict)),
        "working_document_block_count": working_document_block_count(working_document),
        "working_document_text_chars": working_document_text_chars(working_document),
        "provider_log_count_total": len(provider_logs),
        "provider_log_count_delta": max(0, len(provider_logs) - previous_provider_log_count),
        "stage_audit_count": len(stage_audits),
        "stage_audits": [
            {
                "stage_id": dict(item).get("stage_id"),
                "stage_kind": dict(item).get("stage_kind"),
                "validation_status": dict(item).get("validation_status"),
                "adopted_fields": dict(item).get("adopted_fields"),
            }
            for item in stage_audits
        ],
        "post_update_review": post_update_review,
        "review_after_apply_result": review_result,
        "closure_decision": dict(turn.get("closure_decision") or {}),
        "session_phase": session.get("session_phase"),
    }


def run_orchestrator(
    *,
    base_url: str,
    orchestrator_id: str,
    provider_id: str,
    model: str,
    template_id: str,
    topic: str,
    mode: str,
    max_turns: int,
    timeout: float,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_jsonl = output_dir / f"{orchestrator_id}.turns.raw.jsonl"
    metrics_jsonl = output_dir / f"{orchestrator_id}.turns.metrics.jsonl"
    summary_path = output_dir / f"{orchestrator_id}.summary.json"
    final_session_path = output_dir / f"{orchestrator_id}.final-session.json"

    session_payload = {
        "topic": topic,
        "orchestrator_id": orchestrator_id,
        "provider_id": provider_id,
        "model": model,
        "template_id": template_id,
        "knowledge_package_id": "airspace-domain-demo",
        "write_policy": "patch_suggestion_only",
    }
    started_at = datetime.now().isoformat(timespec="seconds")
    try:
        session_response = post_json_with_retry(
            base_url,
            "/api/requirement-analysis/sessions",
            session_payload,
            timeout,
            retries=1,
        )
    except Exception as exc:  # noqa: BLE001 - setup failure is still a test result.
        setup_error = {
            "orchestrator_id": orchestrator_id,
            "phase": "create_session",
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if isinstance(exc, httpx.HTTPStatusError):
            setup_error.update(http_error_payload(exc))
        json_dump(output_dir / f"{orchestrator_id}.session-create-error.json", setup_error)
        summary = {
            "orchestrator_id": orchestrator_id,
            "session_id": None,
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "requested_turns": max_turns,
            "completed_turns": 0,
            "error_count": 1,
            "turn_success_rate": 0,
            "last_error": setup_error,
        }
        json_dump(summary_path, summary)
        return summary
    session_id = str(session_response["session_id"])
    json_dump(output_dir / f"{orchestrator_id}.session-created.json", session_response)

    metrics: list[dict[str, Any]] = []
    previous_provider_log_count = count_list(session_response.get("provider_logs"))
    last_session: dict[str, Any] | None = dict(session_response)
    used_domains: set[str] = set()
    recent_questions: list[str] = []
    for turn_index in range(1, max_turns + 1):
        if mode == "fixed":
            if turn_index > len(DEFAULT_TURNS):
                break
            examiner_decision = {
                "user_input": DEFAULT_TURNS[turn_index - 1],
                "examiner_action": "fixed_regression_input",
                "examiner_reason": "历史 20 回合固定回归链路。",
                "released_domain": f"fixed-{turn_index:02d}",
            }
        else:
            examiner_decision = choose_dynamic_examiner_input(
                turn_index=turn_index,
                max_turns=max_turns,
                last_session=last_session,
                used_domains=used_domains,
                recent_questions=recent_questions,
            )
        user_input = examiner_decision["user_input"]
        turn_started = time.monotonic()
        try:
            response_payload = post_json(
                base_url,
                f"/api/requirement-analysis/sessions/{session_id}/turns",
                {"user_input": user_input},
                timeout,
            )
            elapsed = time.monotonic() - turn_started
            jsonl_append(
                raw_jsonl,
                {
                    "turn_index": turn_index,
                    "elapsed_seconds": round(elapsed, 3),
                    "examiner_decision": examiner_decision,
                    "payload": response_payload,
                },
            )
            item = extract_turn_metrics(
                orchestrator_id=orchestrator_id,
                turn_index=turn_index,
                elapsed_seconds=elapsed,
                user_input=user_input,
                response_payload=response_payload,
                previous_provider_log_count=previous_provider_log_count,
                examiner_action=examiner_decision.get("examiner_action", ""),
                examiner_reason=examiner_decision.get("examiner_reason", ""),
                released_domain=examiner_decision.get("released_domain", ""),
            )
            previous_provider_log_count = int(item["provider_log_count_total"])
            metrics.append(item)
            jsonl_append(metrics_jsonl, item)
            last_session = dict(response_payload.get("session") or {})
            released_domain = str(examiner_decision.get("released_domain") or "")
            if released_domain and not released_domain.startswith("fixed-") and released_domain not in {"convergence", "correction", "initial_intent"}:
                used_domains.add(released_domain)
            if item.get("next_question"):
                recent_questions.append(str(item.get("next_question") or ""))
                recent_questions = recent_questions[-3:]
            print(
                f"{orchestrator_id} turn {turn_index:02d}: ok "
                f"{elapsed:.1f}s assistant={item['assistant_message_chars']} "
                f"patch={item['document_patch_count']} provider_delta={item['provider_log_count_delta']} "
                f"examiner={item['examiner_action']}",
                flush=True,
            )
            if mode == "dynamic" and should_stop_dynamic_probe_after_turn(last_session):
                print(
                    f"{orchestrator_id} turn {turn_index:02d}: stop after {dict(last_session.get('next_interaction') or {}).get('type')}",
                    flush=True,
                )
                break
        except Exception as exc:  # noqa: BLE001 - test runner must preserve exact failure.
            elapsed = time.monotonic() - turn_started
            error_payload = {
                "orchestrator_id": orchestrator_id,
                "turn_index": turn_index,
                "elapsed_seconds": round(elapsed, 3),
                "status": "error",
                "user_input": short_text(user_input, 500),
                "examiner_action": examiner_decision.get("examiner_action", ""),
                "examiner_reason": short_text(examiner_decision.get("examiner_reason", ""), 500),
                "released_domain": examiner_decision.get("released_domain", ""),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            if isinstance(exc, httpx.HTTPStatusError):
                error_payload.update(http_error_payload(exc))
            metrics.append(error_payload)
            jsonl_append(metrics_jsonl, error_payload)
            print(f"{orchestrator_id} turn {turn_index:02d}: error {type(exc).__name__}: {exc}", flush=True)
            break

    try:
        if session_id:
            last_session = get_json(base_url, f"/api/requirement-analysis/sessions/{session_id}", timeout)
            json_dump(final_session_path, last_session)
    except Exception as exc:  # noqa: BLE001
        json_dump(output_dir / f"{orchestrator_id}.final-session-error.json", {"error": str(exc), "error_type": type(exc).__name__})

    ok_count = len([item for item in metrics if item.get("status") == "ok"])
    error_count = len(metrics) - ok_count
    final_decision_state = dict((last_session or {}).get("decision_state") or {})
    final_working_document = dict((last_session or {}).get("working_document") or {})
    summary = {
        "orchestrator_id": orchestrator_id,
        "session_id": session_id,
        "mode": mode,
        "started_at": started_at,
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "requested_turns": max_turns,
        "completed_turns": ok_count,
        "error_count": error_count,
        "turn_success_rate": round(ok_count / max_turns, 4) if max_turns else 0,
        "assistant_message_chars_total": sum(int(item.get("assistant_message_chars") or 0) for item in metrics),
        "document_patch_chars_total": sum(int(item.get("document_patch_chars") or 0) for item in metrics),
        "final_provider_log_count": count_list((last_session or {}).get("provider_logs")),
        "examiner_action_distribution": {
            action: len([item for item in metrics if item.get("examiner_action") == action])
            for action in sorted({str(item.get("examiner_action") or "") for item in metrics if item.get("examiner_action")})
        },
        "released_domains": [
            domain
            for domain in sorted({str(item.get("released_domain") or "") for item in metrics if item.get("released_domain")})
        ],
        "final_working_document_block_count": working_document_block_count(final_working_document),
        "final_working_document_text_chars": working_document_text_chars(final_working_document),
        "final_decision_state_counts": {
            "confirmed_facts": count_list(final_decision_state.get("confirmed_facts")),
            "confirmed_decisions": count_list(final_decision_state.get("confirmed_decisions")),
            "tentative_assumptions": count_list(final_decision_state.get("tentative_assumptions")),
            "open_questions": count_active_open_questions(final_decision_state.get("open_questions")),
            "open_questions_total_retained": count_list(final_decision_state.get("open_questions")),
            "rejected_directions": count_list(final_decision_state.get("rejected_directions")),
            "chapter_projections": count_list(final_decision_state.get("chapter_projections")),
        },
        "last_next_question": metrics[-1].get("next_question") if metrics else "",
        "last_error": metrics[-1] if metrics and metrics[-1].get("status") == "error" else None,
    }
    json_dump(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P2 requirement-analysis orchestrator multi-turn probes.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--orchestrator", action="append", required=True, help="Orchestrator id. Repeatable.")
    parser.add_argument("--provider", default="deepseek", help="P2 provider id.")
    parser.add_argument("--model", default="provider-default", help="P2 model id.")
    parser.add_argument(
        "--template-id",
        default="xg-template-81433-默认运算软件需求规格说明模板实例-v1-0",
        help="Requirement template instance id.",
    )
    parser.add_argument("--topic", default="态势分析系统需求规格探索", help="Session topic.")
    parser.add_argument(
        "--mode",
        choices=["dynamic", "fixed"],
        default="dynamic",
        help="dynamic uses the controlled examiner strategy; fixed uses the historical 20-turn regression chain.",
    )
    parser.add_argument("--max-turns", type=int, default=20, help="Maximum turns to submit.")
    parser.add_argument("--timeout", type=float, default=180, help="Per-request timeout seconds.")
    parser.add_argument("--output-dir", default=".run-logs/p2-orchestrator-iteration", help="Output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for orchestrator_id in args.orchestrator:
        summary = run_orchestrator(
            base_url=args.base_url,
            orchestrator_id=orchestrator_id,
            provider_id=args.provider,
            model=args.model,
            template_id=args.template_id,
            topic=args.topic,
            mode=args.mode,
            max_turns=args.max_turns,
            timeout=args.timeout,
            output_dir=output_root,
        )
        summaries.append(summary)
    json_dump(output_root / "summary.json", summaries)
    print(json.dumps(summaries, ensure_ascii=False, indent=2), flush=True)
    return 1 if any(item.get("error_count") for item in summaries) else 0


if __name__ == "__main__":
    sys.exit(main())
