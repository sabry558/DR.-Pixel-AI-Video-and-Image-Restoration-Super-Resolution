# Dr. Pixel — Frontend Specification v1

## Overview

Dr. Pixel is an AI-powered image and video restoration platform inspired by modern AI SaaS products such as Topaz Labs. The product consists of two major areas:

1. Public Marketing Website
2. Authenticated User Portal

The frontend should be built independently from the backend and later integrated with the existing FastAPI services.

---

# Technology Stack

## Framework

* Next.js 15
* TypeScript
* TailwindCSS
* shadcn/ui
* Framer Motion
* Axios
* TanStack Query
* next-themes

## Design Goals

The interface should feel premium and modern.

Visual inspiration:

* Topaz Labs
* Vercel
* Linear
* Stripe

Avoid:

* Bootstrap appearance
* Admin-dashboard look
* Academic project aesthetics

---

# Branding

## Product Name

Dr. Pixel

## Logo

Use the supplied Dr. Pixel logo.

## Themes

Support:

* Light Theme
* Dark Theme
* System Theme

Theme switching should be available globally.

---

# Public Website

## Navigation

Navbar:

* Home
* Solutions
* Showcase
* Pricing
* About

Actions:

* Login
* Get Started

Footer:

Product

* Solutions
* Showcase
* Pricing

Company

* About

Resources

* API Documentation (placeholder)

Legal

* Privacy Policy
* Terms of Service

---

# Home Page

## Hero Section

Headline:

Restore Every Pixel.
Revive Every Memory.

Subheadline:

AI-powered image and video restoration for damaged, blurry, noisy, and low-quality media.

Buttons:

* Get Started
* View Showcase

Hero visual:

Interactive before/after comparison slider using placeholder media.

---

## Features Section

Display feature cards:

* Super Resolution
* Denoising
* Deblurring
* Color Restoration
* Artifact Removal
* Video Enhancement

---

## How It Works

Three-step workflow:

1. Upload Media
2. AI Processing
3. Download Results

---

## Final CTA

Call to action encouraging account creation.

---

# Solutions Page

Present solution categories:

## Image Restoration

Examples:

* Old photographs
* Family albums
* Damaged scans
* Historical archives

## Video Restoration

Examples:

* VHS footage
* Film restoration
* Low-quality recordings
* Social media videos

## Professional Media Recovery

Examples:

* Studios
* Archivists
* Researchers
* Content creators

---

# Showcase Page

Purpose:

Demonstrate restoration quality.

Structure:

Multiple showcase cards containing:

* Before image/video
* After image/video
* Description
* Restoration improvements

Use placeholder media initially.

Support interactive comparison sliders.

Examples:

* VHS Restoration
* Family Photo Recovery
* Night Video Enhancement
* Historical Footage Restoration

---

# Pricing Page

Display pricing tiers.

## Starter

* Free
* 5 jobs/month
* 720p exports
* Basic restoration

## Pro

* 100 jobs/month
* 1080p exports
* Priority queue

## Studio

* Unlimited jobs
* 4K exports
* Highest priority queue

Pricing does not need billing integration initially.

---

# About Page

Introduce Dr. Pixel.

Explain mission:

Using AI to restore memories and improve visual quality.

Display logo and brand story.

---

# Authentication

## Login Page

Fields:

* Email
* Password

Actions:

* Login
* Forgot Password

---

## Registration Page

Fields:

* Name
* Email
* Password
* Confirm Password

Actions:

* Create Account

---

# User Portal

Route Prefix:

/portal

---

# Portal Navigation

Sidebar:

* Dashboard
* Image Restoration
* Video Restoration
* Jobs
* Billing
* Settings

---

# Dashboard

Display summary cards:

* Total Jobs
* Completed Jobs
* Processing Jobs
* Failed Jobs

Display Recent Jobs table.

Display Usage Summary.

---

# Image Restoration Page

## Upload Area

Drag-and-drop upload zone.

## Options

* Model Selection
* Scale Selection
* Enhancement Settings

Example settings:

* Denoise
* Sharpen
* Face Recovery

## Action

Restore Image

Workflow:

Create job and redirect to Jobs page.

---

# Video Restoration Page

## Upload Area

Video upload component.

## Options

Resolution:

* Original
* 720p
* 1080p
* 4K

Frame Rate:

* 30 FPS
* 60 FPS

Enhancements:

* Denoise
* Stabilization
* Frame Interpolation

## Action

Start Restoration

Workflow:

Create job and redirect to Jobs page.

---

# Jobs Page

Purpose:

Track asynchronous processing.

Columns:

* Job Name
* Media Type
* Status
* Progress
* Created Date
* Download Result

Statuses:

* Queued
* Processing
* Completed
* Failed

---

# Billing Page

Display:

* Current Plan
* Monthly Usage
* Upgrade Options

Placeholder implementation acceptable.

---

# Settings Page

Sections:

## Appearance

* Light
* Dark
* System

## Account

* Profile Information
* Change Password

## Security

* Session Management

---

# Backend Integration

The frontend must be structured to integrate later with FastAPI endpoints.

Expected areas:

Authentication:

* /auth

Images:

* /image

Videos:

* /video

Jobs:

* /jobs

Health:

* /health

Use service abstraction layers for API communication.

---

# Future Enhancements

* Team accounts
* API keys
* Usage analytics
* Model marketplace
* Batch processing
* Notifications
* Real-time WebSocket updates

These features should not be implemented in v1 but the architecture should allow future expansion.
