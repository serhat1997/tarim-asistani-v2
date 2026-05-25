from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal, InvalidOperation
import datetime

from .models import Field, HarvestEntry, FieldExpense, LandTransaction, PRODUCT_CHOICES, UNIT_CHOICES, EXPENSE_CATEGORIES
from transactions.models import Transaction as TxModel


def _land_stats(field):
    """Compute land profitability stats for a field. Returns a dict."""
    txns = list(field.land_transactions.all())
    purchases = [t for t in txns if t.transaction_type == 'alis']
    sales     = [t for t in txns if t.transaction_type == 'satis']

    total_purchase_area = sum(t.area_decare for t in purchases) or Decimal('0')
    total_purchase_cost = sum(t.net_amount   for t in purchases) or Decimal('0')  # includes fees
    avg_cost_per_dec    = (total_purchase_cost / total_purchase_area) if total_purchase_area else Decimal('0')

    total_sale_area    = sum(t.area_decare for t in sales) or Decimal('0')
    total_sale_revenue = sum(t.net_amount  for t in sales) or Decimal('0')  # minus fees
    avg_sale_per_dec   = (total_sale_revenue / total_sale_area) if total_sale_area else Decimal('0')

    # Proportional purchase cost for the sold area
    prop_purchase_cost = avg_cost_per_dec * total_sale_area
    land_profit        = total_sale_revenue - prop_purchase_cost
    land_profit_per_dec = (land_profit / total_sale_area) if total_sale_area else Decimal('0')
    land_roi = ((land_profit / prop_purchase_cost) * 100) if prop_purchase_cost else Decimal('0')

    # Annotate each sale with per-sale profit
    for s in sales:
        s.profit_per_dec = s.effective_price_per_decare - avg_cost_per_dec
        s.total_profit   = s.profit_per_dec * s.area_decare
        s.roi_pct        = ((s.profit_per_dec / avg_cost_per_dec) * 100) if avg_cost_per_dec else Decimal('0')
        s.is_profit      = s.profit_per_dec >= 0

    return {
        'purchases': purchases,
        'sales': sales,
        'total_purchase_area': total_purchase_area,
        'total_purchase_cost': total_purchase_cost,
        'avg_cost_per_dec': avg_cost_per_dec,
        'total_sale_area': total_sale_area,
        'total_sale_revenue': total_sale_revenue,
        'avg_sale_per_dec': avg_sale_per_dec,
        'land_profit': land_profit,
        'land_profit_per_dec': land_profit_per_dec,
        'land_roi': land_roi,
        'has_purchase': bool(purchases),
        'has_sale': bool(sales),
    }


@login_required
def field_list(request):
    fields = Field.objects.filter(user=request.user).prefetch_related(
        'harvests', 'expenses', 'land_transactions', 'transactions'
    )
    field_data = []
    for f in fields:
        ls = _land_stats(f)

        harvest_rev = sum(h.amount for h in f.harvests.all())
        tx_rev      = sum(t.amount for t in f.transactions.all() if t.type == 'sale')
        total_rev   = harvest_rev + tx_rev

        field_exp   = sum(e.amount for e in f.expenses.all())
        tx_exp      = sum(t.amount for t in f.transactions.all() if t.type == 'purchase')
        total_exp   = field_exp + tx_exp

        agri_net     = total_rev - total_exp
        agri_per_dec = (agri_net / f.area) if f.area else Decimal('0')
        field_data.append({
            'field': f,
            'total_rev': total_rev,
            'total_exp': total_exp,
            'agri_net': agri_net,
            'agri_per_dec': agri_per_dec,
            'avg_cost_per_dec': ls['avg_cost_per_dec'],
            'avg_sale_per_dec': ls['avg_sale_per_dec'],
            'land_profit_per_dec': ls['land_profit_per_dec'],
            'has_purchase': ls['has_purchase'],
            'has_sale': ls['has_sale'],
        })
    return render(request, 'fields/field_list.html', {'field_data': field_data})


@login_required
def field_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        area = request.POST.get('area', '').strip().replace(',', '.')
        crop_type = request.POST.get('crop_type', '').strip()
        notes = request.POST.get('notes', '').strip()
        if not name or not area:
            messages.error(request, 'Tarla adı ve alan zorunludur.')
            return render(request, 'fields/field_form.html', {'form_data': request.POST})
        try:
            area_val = Decimal(area)
        except InvalidOperation:
            messages.error(request, 'Geçerli bir alan değeri girin.')
            return render(request, 'fields/field_form.html', {'form_data': request.POST})
        Field.objects.create(user=request.user, name=name, area=area_val, crop_type=crop_type, notes=notes)
        messages.success(request, f'"{name}" tarlası eklendi.')
        return redirect('field_list')
    return render(request, 'fields/field_form.html', {})


@login_required
def field_detail(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    harvests = field.harvests.all()
    expenses = field.expenses.all()

    # Bağlı işlemler (transactions sekmesinden tarla seçilerek girilmiş)
    linked_txns     = list(field.transactions.select_related('customer').order_by('-date'))
    linked_sales    = [t for t in linked_txns if t.type == 'sale']
    linked_purchases = [t for t in linked_txns if t.type == 'purchase']
    linked_revenue  = sum(t.amount for t in linked_sales)
    linked_expense  = sum(t.amount for t in linked_purchases)

    # Tarımsal toplamlar: hasat + bağlı satışlar → gelir; gider + bağlı alışlar → gider
    harvest_revenue = sum(h.amount for h in harvests)
    field_expenses  = sum(e.amount for e in expenses)
    total_revenue   = harvest_revenue + linked_revenue
    total_expense   = field_expenses + linked_expense
    agri_net        = total_revenue - total_expense
    agri_net_per_dec = (agri_net / field.area) if field.area else Decimal('0')

    ls = _land_stats(field)

    ctx = {
        'field': field,
        'harvests': harvests,
        'expenses': expenses,
        'harvest_revenue': harvest_revenue,
        'field_expenses': field_expenses,
        'linked_txns': linked_txns,
        'linked_sales': linked_sales,
        'linked_purchases': linked_purchases,
        'linked_revenue': linked_revenue,
        'linked_expense': linked_expense,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'agri_net': agri_net,
        'agri_net_per_dec': agri_net_per_dec,
        'product_choices': PRODUCT_CHOICES,
        'unit_choices': UNIT_CHOICES,
        'expense_categories': EXPENSE_CATEGORIES,
        'today': datetime.date.today().isoformat(),
        **ls,
    }
    return render(request, 'fields/field_detail.html', ctx)


@login_required
def field_edit(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        area = request.POST.get('area', '').strip().replace(',', '.')
        crop_type = request.POST.get('crop_type', '').strip()
        notes = request.POST.get('notes', '').strip()
        if not name or not area:
            messages.error(request, 'Tarla adı ve alan zorunludur.')
            return render(request, 'fields/field_form.html', {'field': field, 'form_data': request.POST})
        try:
            field.area = Decimal(area)
        except InvalidOperation:
            messages.error(request, 'Geçerli bir alan değeri girin.')
            return render(request, 'fields/field_form.html', {'field': field, 'form_data': request.POST})
        field.name = name
        field.crop_type = crop_type
        field.notes = notes
        field.save()
        messages.success(request, f'"{name}" güncellendi.')
        return redirect('field_detail', pk=field.pk)
    return render(request, 'fields/field_form.html', {'field': field})


@login_required
def field_delete(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    if request.method == 'POST':
        name = field.name
        field.delete()
        messages.success(request, f'"{name}" tarlası silindi.')
        return redirect('field_list')
    return redirect('field_detail', pk=pk)


@login_required
def harvest_add(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    if request.method == 'POST':
        date_str  = request.POST.get('date', '').strip()
        product   = request.POST.get('product', '').strip()
        quantity  = request.POST.get('quantity', '').strip().replace(',', '.')
        unit      = request.POST.get('unit', 'kg').strip()
        unit_price = request.POST.get('unit_price', '0').strip().replace(',', '.')
        notes     = request.POST.get('notes', '').strip()
        try:
            date_val  = datetime.date.fromisoformat(date_str)
            qty_val   = Decimal(quantity)
            price_val = Decimal(unit_price) if unit_price else Decimal('0')
        except (ValueError, InvalidOperation):
            messages.error(request, 'Geçersiz tarih veya miktar.')
            return redirect('field_detail', pk=pk)
        HarvestEntry.objects.create(
            field=field, date=date_val, product=product,
            quantity=qty_val, unit=unit, unit_price=price_val, notes=notes
        )
        messages.success(request, 'Hasat kaydı eklendi.')
    return redirect('field_detail', pk=pk)


@login_required
def expense_add(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    if request.method == 'POST':
        date_str    = request.POST.get('date', '').strip()
        category    = request.POST.get('category', '').strip()
        amount      = request.POST.get('amount', '').strip().replace(',', '.')
        description = request.POST.get('description', '').strip()
        try:
            date_val   = datetime.date.fromisoformat(date_str)
            amount_val = Decimal(amount)
        except (ValueError, InvalidOperation):
            messages.error(request, 'Geçersiz tarih veya tutar.')
            return redirect('field_detail', pk=pk)
        FieldExpense.objects.create(
            field=field, date=date_val, category=category,
            amount=amount_val, description=description
        )
        messages.success(request, 'Gider kaydı eklendi.')
    return redirect('field_detail', pk=pk)


@login_required
def harvest_delete(request, pk, hpk):
    entry = get_object_or_404(HarvestEntry, pk=hpk, field__pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Hasat kaydı silindi.')
    return redirect('field_detail', pk=pk)


@login_required
def expense_delete(request, pk, epk):
    expense = get_object_or_404(FieldExpense, pk=epk, field__pk=pk)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Gider kaydı silindi.')
    return redirect('field_detail', pk=pk)


@login_required
def land_transaction_add(request, pk):
    field = get_object_or_404(Field, pk=pk, user=request.user)
    if request.method == 'POST':
        tx_type      = request.POST.get('transaction_type', '').strip()
        date_str     = request.POST.get('date', '').strip()
        area         = request.POST.get('area_decare', '').strip().replace(',', '.')
        price        = request.POST.get('price_per_decare', '').strip().replace(',', '.')
        add_costs    = request.POST.get('additional_costs', '0').strip().replace(',', '.')
        counterparty = request.POST.get('counterparty', '').strip()
        deed_no      = request.POST.get('deed_no', '').strip()
        notes        = request.POST.get('notes', '').strip()
        try:
            date_val  = datetime.date.fromisoformat(date_str)
            area_val  = Decimal(area)
            price_val = Decimal(price)
            costs_val = Decimal(add_costs) if add_costs else Decimal('0')
        except (ValueError, InvalidOperation):
            messages.error(request, 'Geçersiz tarih, alan veya fiyat değeri.')
            return redirect('field_detail', pk=pk)
        if tx_type not in ('alis', 'satis'):
            messages.error(request, 'İşlem türü seçiniz.')
            return redirect('field_detail', pk=pk)
        LandTransaction.objects.create(
            field=field,
            transaction_type=tx_type,
            date=date_val,
            area_decare=area_val,
            price_per_decare=price_val,
            additional_costs=costs_val,
            counterparty=counterparty,
            deed_no=deed_no,
            notes=notes,
        )
        label = 'Alış' if tx_type == 'alis' else 'Satış'
        messages.success(request, f'Arazi {label} kaydı eklendi.')
    return redirect('field_detail', pk=pk)


@login_required
def land_transaction_delete(request, pk, lpk):
    txn = get_object_or_404(LandTransaction, pk=lpk, field__pk=pk)
    if request.method == 'POST':
        txn.delete()
        messages.success(request, 'Arazi işlem kaydı silindi.')
    return redirect('field_detail', pk=pk)
