# Business Requirements Document

## Project

StayWise — Hospitality Revenue & Decision Intelligence Platform

## Business Problem

Hotel leadership lacks a unified view of revenue leakage caused by cancellations, underutilized inventory, and unprofitable distribution channels. Current reporting describes bookings but does not help stakeholders decide which intervention should be prioritized.

## Objectives

- Define trusted KPIs for revenue, occupancy, ADR, RevPAR, net RevPAR, cancellation rate, lost revenue, and channel profitability.
- Identify which segments, channels, and booking behaviors create the largest revenue leakage.
- Provide a scenario model for evaluating cancellation, ADR, occupancy, and channel-mix interventions.
- Deliver a Mac-ready decision dashboard and Power BI-ready datasets for stakeholder review.

## Stakeholders

- General Manager: revenue recovery and operating performance.
- Revenue Manager: pricing, cancellation policy, and channel mix.
- Marketing Lead: direct booking and segment targeting.
- Operations Manager: pre-arrival workflows and service interventions.
- Finance Analyst: KPI definitions and revenue reconciliation.

## Functional Requirements

- Load raw hotel booking data and preserve it separately from processed datasets.
- Create a dimensional model with booking facts and conformed business dimensions.
- Calculate cancellation rate, realized revenue, lost revenue, occupancy, ADR, RevPAR, net RevPAR, and channel commission cost.
- Segment revenue leakage by property, market segment, channel, lead-time band, customer type, and deposit type.
- Rank opportunities by recoverable revenue and recommended intervention.
- Export Power BI-ready CSVs and DAX measure definitions.
- Generate an Excel scenario model with editable assumptions.
- Provide a local dashboard that supports the executive decision workflow on macOS.

## Non-Functional Requirements

- Analysis must be reproducible from command line.
- Metric definitions must be documented and traceable.
- Synthetic data must be clearly labeled.
- Dashboard outputs must be understandable to non-technical stakeholders.

## Out of Scope

- Live hotel PMS integration.
- Real-time data refresh.
- Deployment of a production Power BI service workspace.
- Actual policy rollout measurement after implementation.
