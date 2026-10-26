"""Backend-generated academic report and standalone figures from active analysis."""
from __future__ import annotations

import io
import math
from datetime import datetime, timezone
from html import escape

import numpy as np
from matplotlib.figure import Figure
from matplotlib import font_manager
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def render_analysis_chart(analysis, output_format='png') -> bytes:
    """Export actual backend predictions, observations and regression residuals."""
    fit, opt = analysis.fit, analysis.optimization
    p = np.linspace(analysis.configuration['p_min'], analysis.configuration['p_max'], 400)
    demand = fit.coefficients.predict(p)
    realized = np.maximum(0, demand)
    if analysis.configuration['capacity'] is not None:
        realized = np.minimum(realized, analysis.configuration['capacity'])
    fig = Figure(figsize=(8.3, 8.8), layout='constrained', facecolor='white')
    demand_ax, revenue_ax, residual_ax = fig.subplots(3, 1)
    demand_ax.scatter(fit.prices_train, fit.demand_actual, s=16, alpha=.5, color='#64748B', label='Observed sales')
    demand_ax.plot(p, demand, color='#4F46E5', label='Fitted demand')
    demand_ax.plot(p, realized, color='#10B981', linestyle='--', label='Capacity-adjusted demand')
    demand_ax.set(ylabel='Tickets', title='Demand and historical observations')
    demand_ax.legend(fontsize=8)
    revenue_ax.plot(p, p * realized, color='#4F46E5', label='Feasible modeled revenue')
    if opt and opt.optimal_price is not None:
        revenue_ax.scatter([opt.optimal_price], [opt.optimal_realized_revenue], color='#10B981', s=45, zorder=4, label='Best compared candidate')
    revenue_ax.set(ylabel='Revenue (INR)', title='Revenue within configured price interval')
    revenue_ax.legend(fontsize=8)
    residual_ax.scatter(fit.demand_predicted, fit.residuals, s=17, color='#4F46E5', alpha=.6)
    residual_ax.axhline(0, color='#64748B', linewidth=.8)
    residual_ax.set(xlabel='Predicted tickets', ylabel='Residual (tickets)', title='Full-data residuals: actual minus predicted')
    for ax in (demand_ax, revenue_ax):
        ax.set_xlabel('Ticket price (INR)')
    for ax in (demand_ax, revenue_ax, residual_ax):
        ax.grid(alpha=.15)
        ax.spines[['top', 'right']].set_visible(False)
    buf = io.BytesIO()
    fig.savefig(buf, format=output_format, dpi=160)
    fig.clear()
    return buf.getvalue()


def _number(value, digits=4):
    if value is None or not math.isfinite(value):
        return 'Undefined / unavailable'
    return f'{value:,.{digits}f}'


def generate_analysis_pdf(analysis) -> bytes:
    """Paginated report with current settings and the complete numerical evidence."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, PageBreak, Image, KeepTogether)

    # Matplotlib ships these fonts, so report generation needs no online assets.
    for name, weight in [('PP', 'normal'), ('PPBold', 'bold')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, font_manager.findfont(
                font_manager.FontProperties(family='DejaVu Sans', weight=weight))))
    pdfmetrics.registerFontFamily('PP', normal='PP', bold='PPBold', italic='PP', boldItalic='PPBold')
    styles = getSampleStyleSheet()
    body = ParagraphStyle('PPBody', parent=styles['BodyText'], fontName='PP', fontSize=9, leading=14, spaceAfter=7)
    title = ParagraphStyle('PPTitle', parent=body, fontName='PPBold', fontSize=27, leading=34, textColor=colors.HexColor('#101828'), spaceAfter=10)
    heading = ParagraphStyle('PPHeading', parent=body, fontName='PPBold', fontSize=15, leading=20, textColor=colors.HexColor('#4F46E5'), spaceBefore=12, spaceAfter=8)
    small = ParagraphStyle('PPSmall', parent=body, fontSize=7, leading=10, spaceAfter=0)
    story = []
    width = A4[0] - 36*mm
    def para(text, style=body):
        return Paragraph(escape(str(text)).replace('\n','<br/>'), style)
    def add(text, style=body):
        story.append(para(text, style))
    def section(text):
        add(text, heading)
    def table(headers, rows, widths=None, tiny=False):
        style = small if tiny else body
        grid = [[para(v, small) for v in headers]]
        grid += [[para(v, style) for v in row] for row in rows]
        t = Table(grid, colWidths=widths or [width/len(headers)]*len(headers), repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EAFB')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F8FAFC')]),
            ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#C7D2FE')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.append(t)
        story.append(Spacer(1,8))

    fit, comp, opt = analysis.fit, analysis.comparison, analysis.optimization
    request = analysis.request
    add('PricePilot', title)
    add('EVENT REVENUE OPTIMIZER · ACADEMIC ANALYSIS')
    add('Find the right ticket price. Understand the mathematics.')
    add('Generated UTC: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))
    section('1. Dataset and analysis context')
    add(request.dataset_name)
    add('SYNTHETIC DEMONSTRATION DATA — NOT REAL HISTORICAL SALES' if request.is_synthetic else 'User-supplied dataset. Provenance and real-world validity have not been independently verified.')
    add(f'{len(request.observations)} valid observations supplied; final models refitted on all observations. Holdout scores below come from training-only fits, not from the final refit.')
    table(['Setting','Active value'], [[k.replace('_',' ').title(), v if v is not None else 'Not specified'] for k,v in analysis.configuration.items()], [width*.45,width*.55])
    section('2. Model comparison')
    add('Recommendation: ' + comp.recommended_model + '. ' + comp.recommendation_reason)
    add(f'Holdout available: {comp.has_validation}; split training size {comp.train_size}, validation size {comp.val_size}; strategy {comp.split_strategy}, seed 42, not chronological.')
    story.append(PageBreak())
    section('3. Fitted demand models and diagnostics')
    for model, heldout in [(comp.linear,comp.linear_val),(comp.quadratic,comp.quadratic_val)]:
        if model is None:
            continue
        add(model.model_type.title() + ': ' + model.coefficients.equation_str)
        table(['Metric','Full-data fit','Held-out evaluation'], [
            ['Observations',model.n_samples,heldout.n_samples if heldout else 'Unavailable'],
            ['SSE',_number(model.sse),_number(heldout.sse) if heldout else 'Unavailable'],
            ['MAE (tickets)',_number(model.mae),_number(heldout.mae) if heldout else 'Unavailable'],
            ['RMSE (tickets)',_number(model.rmse),_number(heldout.rmse) if heldout else 'Unavailable'],
            ['R²',_number(model.r_squared),_number(heldout.r_squared) if heldout else 'Unavailable'],
            ['Adjusted R²',_number(model.adjusted_r_squared),'Not interpreted for holdout'],
            ['Scaled design condition',_number(model.condition_number),'Not applicable']])
        for warning in model.warnings:
            add('Model warning: ' + warning)
    section('4. Mathematical construction')
    add('Linear: D(p)=a+bp; R(p)=ap+bp²; R′(p)=a+2bp; R″(p)=2b.')
    add('Quadratic: D(p)=a+bp+cp²; R(p)=ap+bp²+cp³; R′(p)=a+2bp+3cp²; R″(p)=2b+6cp.')
    add('Least squares minimizes Σ[Dᵢ−D(pᵢ)]². XᵀXβ=Xᵀy describes the normal equations. The implementation solves a centered/scaled design with NumPy lstsq (SVD), without explicitly inverting XᵀX.')
    add('Selected model normal-equation matrix (original units, for explanation):')
    for row in fit.normal_equation_matrix:
        add('   '.join(f'{v:.6g}' for v in row), small)
    add('Right-hand side: ' + ', '.join(f'{v:.6g}' for v in fit.normal_equation_rhs), small)
    story.append(PageBreak())
    section('5. Predictions and residual evidence')
    add('All curves and residuals below are generated by the backend from the active full-data fit. Fractional predicted ticket counts are expected values, not guaranteed sales.')
    story.append(Image(io.BytesIO(render_analysis_chart(analysis)), width=width, height=width*8.8/8.3))
    story.append(PageBreak())
    section('6. Feasible revenue optimization')
    add('Expected realized sales = min(capacity, max(0,D(p))) when capacity is supplied. Negative-demand candidates are rejected. This is gross ticket revenue; costs and profit are not modeled.')
    if opt.optimal_price is not None:
        table(['Result','Computed value'], [
            ['Selected model',analysis.configuration['model_type']],
            ['Best compared price (INR)',_number(opt.optimal_price,6)],
            ['Predicted unconstrained demand',_number(opt.optimal_demand)],
            ['Expected capacity-adjusted sales',_number(opt.optimal_realized_demand)],
            ['Expected realized revenue (INR)',_number(opt.optimal_realized_revenue,2)],
            ['Candidate source',opt.optimal_source],
            ['Classification',opt.optimal_classification],
            ['Newton convergence',str(opt.newton_converged)],
            ['Newton status',opt.newton_status],
            ['Newton stationary type',opt.newton_stationary_type],
            ['R″ at Newton root',_number(opt.newton_second_derivative)],
            ['Grid cross-check',f'Agrees: {opt.scan_agrees}; discrepancy {_number(opt.scan_tolerance_pct,8)}% (acceptance < 2%)']])
        if opt.newton_stationary_price is not None:
            a,b,c = fit.coefficients.a,fit.coefficients.b,fit.coefficients.c or 0
            root = opt.newton_stationary_price
            add('Actual derivative residual |R′(p)| = ' + _number(abs(a+2*b*root+3*c*root*root),10))
    else:
        add('No feasible optimum was obtained. ' + opt.optimal_classification)
    add('Newton solves f(p)=R′(p)=0 via pₖ₊₁=pₖ−f(pₖ)/f′(pₖ). Convergence alone is not proof of a maximum: check R″, feasibility, boundaries and capacity breakpoints. A failed Newton run can still be accompanied by a valid boundary or analytic candidate result.')
    section('7. Complete Newton iteration trace')
    if opt.iterations:
        table(['k','pₖ','R′(pₖ)','R″(pₖ)','Correction','pₖ₊₁'], [
            [it.iteration, _number(it.price,6), _number(it.f_value,6),_number(it.f_prime,6), _number(it.correction,6), _number(it.next_price,6)] for it in opt.iterations], tiny=True)
        for it in opt.iterations:
            if it.convergence_note:
                add(f'Iteration {it.iteration}: {it.convergence_note}', small)
    else:
        add('No Newton iterations were performed.')
    section('8. Compared candidate points')
    table(['Source','Price INR','Demand','Realized revenue INR','Feasible'], [
        [c.source,_number(c.price,5),_number(c.demand,2),_number(c.realized_revenue,2),str(c.is_feasible)] for c in opt.candidates], tiny=True)
    for candidate in opt.candidates:
        if candidate.notes:
            add(candidate.source + ': ' + candidate.notes, small)
    section('9. Price-revenue scenario comparison')
    add(f'Baseline price: INR {_number(request.baseline_price or analysis.configuration["p_min"],2)}. Hypothetical demand multiplier: {request.demand_multiplier:g}. This assumption is not a fitted causal estimate. It affects these scenarios only; the base optimization above uses the fitted model unchanged.')
    table(['Price INR','Predicted demand','Realized sales','Realized revenue INR','Feasible'], [
        [_number(s.price,2),_number(s.predicted_demand,2),_number(s.realized_demand,2),_number(s.realized_revenue,2),str(s.is_feasible)] for s in analysis.scenarios], tiny=True)
    section('10. Warnings, assumptions and limitations')
    for warning in analysis.warnings:
        add('Warning: ' + warning)
    for limitation in [
        'A price-only regression omits marketing, performers, timing, popularity and other confounders. Association does not establish a causal price effect.',
        'Pooled records must represent comparable demand conditions. A category label does not prove comparability.',
        'A random holdout of synthetic or historical observations is not independent real-world validation. No confidence interval or guaranteed uplift is claimed.',
        'Sold-out observations are capacity-censored. Ordinary least squares is not a censored-demand estimator.',
        'Polynomial behavior outside observed prices may be economically implausible. Interpret boundary recommendations and increasing demand with caution.',
        'The model optimizes expected gross ticket revenue, not profit, event welfare, uncertainty or multi-tier pricing.'
    ]:
        add(limitation)
    section('11. Conclusion and methodology notes')
    if opt.optimal_price is not None:
        add(f'For the selected {analysis.configuration["model_type"]} model and active constraints, the best feasible compared price is INR {_number(opt.optimal_price,2)}, with expected realized sales {_number(opt.optimal_realized_demand,2)} and revenue INR {_number(opt.optimal_realized_revenue,2)}. This is a model-based estimate subject to the warnings above.')
    else:
        add('The supplied configuration did not yield a valid recommendation. Review the data and feasibility warnings before making a decision.')

    def footer(canvas, doc):
        canvas.setFont('PP',7)
        canvas.setFillColor(colors.HexColor('#64748B'))
        canvas.drawString(18*mm,12*mm,'PricePilot · Backend-computed academic analysis')
        canvas.drawRightString(A4[0]-18*mm,12*mm,f'Page {doc.page}')
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=20*mm,title='PricePilot academic analysis',author='PricePilot')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
