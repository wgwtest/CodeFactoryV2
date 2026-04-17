from __future__ import annotations

from app.software_design.models import (
    ModuleWorkorderBatchPackage,
    P3Order,
    P3OrderDetail,
    P3OrderSummary,
    PackageSummary,
    RequirementSpecSummary,
    ReviewThread,
    SoftwareDesignBaseline,
    SoftwareDesignDescription,
    SoftwareDesignMetrics,
    SoftwareDesignOverview,
)


def project_order_summary(order: P3Order) -> P3OrderSummary:
    return P3OrderSummary(
        order_id=order.order_id,
        requirement_spec_id=order.requirement_spec_id,
        application_name=order.application_name,
        status=order.status,
        updated_at=order.updated_at,
    )


def project_order_list(orders: list[P3Order]) -> list[P3OrderSummary]:
    return [project_order_summary(order) for order in orders]


def project_package_summary(package: ModuleWorkorderBatchPackage) -> PackageSummary:
    return PackageSummary(
        package_id=package.package_id,
        order_id=package.order_id,
        item_count=len(package.items),
        push_status=package.push_status,
    )


def project_overview(
    orders: list[P3Order],
    packages: list[ModuleWorkorderBatchPackage],
) -> SoftwareDesignOverview:
    return SoftwareDesignOverview(
        metrics=SoftwareDesignMetrics(
            order_count=len(orders),
            pending_approval_count=sum(1 for order in orders if order.status == "pending_approval"),
            frozen_count=sum(1 for order in orders if order.status == "frozen"),
            package_ready_count=sum(1 for order in orders if order.status == "package_ready"),
            pushed_count=sum(1 for order in orders if order.status == "pushed_to_p4"),
        ),
        recent_orders=project_order_list(orders[:5]),
        recent_packages=[project_package_summary(package) for package in packages[:5]],
    )


def project_order_detail(
    order: P3Order,
    baseline: SoftwareDesignBaseline | None,
    review_threads: list[ReviewThread],
    package: ModuleWorkorderBatchPackage | None,
) -> P3OrderDetail:
    return P3OrderDetail(
        order_id=order.order_id,
        status=order.status,
        requirement_spec_summary=RequirementSpecSummary(
            application_name=order.application_name,
            domain_name=order.domain_name,
            status=order.requirement_spec_status,
        ),
        design_description=SoftwareDesignDescription(
            sections=baseline.sections,
            modules=baseline.modules,
        )
        if baseline
        else None,
        review_threads=review_threads,
        workorder_batch=package,
    )
