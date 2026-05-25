from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal, InvalidOperation
import datetime

from .models import InventoryItem, CATEGORIES, UNITS
from customers.models import Customer


@login_required
def inventory_list(request):
    cat_filter = request.GET.get('cat', '')
    status_filter = request.GET.get('status', '')

    items = InventoryItem.objects.filter(user=request.user)
    if cat_filter and cat_filter != 'all':
        items = items.filter(category=cat_filter)

    items = list(items)
    if status_filter == 'elde':
        items = [i for i in items if not i.is_sold]
    elif status_filter == 'satildi':
        items = [i for i in items if i.is_sold]

    # Summary stats
    total_purchase = sum(i.purchase_price for i in items)
    sold_items     = [i for i in items if i.is_sold]
    held_items     = [i for i in items if not i.is_sold]
    total_sold_rev = sum(i.sale_price for i in sold_items)
    total_held_val = sum(i.purchase_price for i in held_items)
    total_profit   = sum(i.profit for i in sold_items if i.profit is not None)

    ctx = {
        'items': items,
        'categories': CATEGORIES,
        'units': UNITS,
        'cat_filter': cat_filter,
        'status_filter': status_filter,
        'total_purchase': total_purchase,
        'total_sold_rev': total_sold_rev,
        'total_held_val': total_held_val,
        'total_profit': total_profit,
        'sold_count': len(sold_items),
        'held_count': len(held_items),
        'today': datetime.date.today().isoformat(),
    }
    return render(request, 'inventory/inventory_list.html', ctx)


def _item_to_initial(item):
    return {
        'name':           item.name,
        'category':       item.category,
        'model_info':     item.model_info,
        'quantity':       item.quantity,
        'unit':           item.unit,
        'purchase_price': item.purchase_price,
        'purchase_date':  item.purchase_date.isoformat() if item.purchase_date else '',
        'sale_quantity':  item.sale_quantity if item.sale_quantity is not None else '',
        'sale_price':     item.sale_price if item.sale_price is not None else '',
        'sale_date':      item.sale_date.isoformat() if item.sale_date else '',
        'notes':          item.notes,
    }


def _get_customers(user):
    return Customer.objects.filter(user=user).order_by('name')


@login_required
def inventory_create(request):
    if request.method == 'POST':
        return _save_item(request, None)
    return render(request, 'inventory/inventory_form.html', {
        'categories': CATEGORIES,
        'units': UNITS,
        'today': datetime.date.today().isoformat(),
        'initial': {},
        'customers': _get_customers(request.user),
    })


@login_required
def inventory_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    if request.method == 'POST':
        return _save_item(request, item)
    return render(request, 'inventory/inventory_form.html', {
        'item': item,
        'categories': CATEGORIES,
        'units': UNITS,
        'today': datetime.date.today().isoformat(),
        'initial': _item_to_initial(item),
        'customers': _get_customers(request.user),
    })


@login_required
def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'"{name}" envanterden silindi.')
    return redirect('inventory_list')


def _save_item(request, item):
    name           = request.POST.get('name', '').strip()
    category       = request.POST.get('category', 'diger').strip()
    model_info     = request.POST.get('model_info', '').strip()
    quantity_raw   = request.POST.get('quantity', '1').strip().replace(',', '.')
    unit           = request.POST.get('unit', 'adet').strip()
    purchase_raw   = request.POST.get('purchase_price', '').strip().replace(',', '.')
    purchase_date  = request.POST.get('purchase_date', '').strip()
    sale_raw       = request.POST.get('sale_price', '').strip().replace(',', '.')
    sale_date_raw  = request.POST.get('sale_date', '').strip()
    notes          = request.POST.get('notes', '').strip()

    sale_qty_raw = request.POST.get('sale_quantity', '').strip().replace(',', '.')

    errors = []
    if not name:
        errors.append('Envanter adı zorunludur.')
    if not purchase_raw:
        errors.append('Alış tutarı zorunludur.')
    if not purchase_date:
        errors.append('Alınış tarihi zorunludur.')

    try:
        qty_val = Decimal(quantity_raw) if quantity_raw else Decimal('1')
    except InvalidOperation:
        errors.append('Geçerli bir adet değeri girin.')
        qty_val = Decimal('1')

    try:
        purchase_val = Decimal(purchase_raw) if purchase_raw else Decimal('0')
    except InvalidOperation:
        errors.append('Geçerli bir alış tutarı girin.')
        purchase_val = Decimal('0')

    try:
        purchase_date_val = datetime.date.fromisoformat(purchase_date) if purchase_date else None
    except ValueError:
        errors.append('Geçerli bir alış tarihi girin.')
        purchase_date_val = None

    sale_qty_val = None
    if sale_qty_raw:
        try:
            sale_qty_val = Decimal(sale_qty_raw)
        except InvalidOperation:
            errors.append('Geçerli bir satış adedi girin.')

    sale_val = None
    if sale_raw:
        try:
            sale_val = Decimal(sale_raw)
        except InvalidOperation:
            errors.append('Geçerli bir satış tutarı girin.')

    sale_date_val = None
    if sale_date_raw:
        try:
            sale_date_val = datetime.date.fromisoformat(sale_date_raw)
        except ValueError:
            errors.append('Geçerli bir satış tarihi girin.')

    sale_customer_id     = request.POST.get('sale_customer') or None
    purchase_customer_id = request.POST.get('purchase_customer') or None

    if errors:
        for e in errors:
            messages.error(request, e)
        initial = {
            'name': name, 'category': category, 'model_info': model_info,
            'quantity': quantity_raw, 'unit': unit,
            'purchase_price': purchase_raw, 'purchase_date': purchase_date,
            'sale_quantity': sale_qty_raw,
            'sale_price': sale_raw, 'sale_date': sale_date_raw,
            'notes': notes,
            'sale_customer': sale_customer_id or '',
            'purchase_customer': purchase_customer_id or '',
        }
        return render(request, 'inventory/inventory_form.html', {
            'item': item,
            'categories': CATEGORIES,
            'units': UNITS,
            'initial': initial,
            'today': datetime.date.today().isoformat(),
            'customers': _get_customers(request.user),
        })

    if item is None:
        saved = InventoryItem.objects.create(
            user=request.user,
            name=name, category=category, model_info=model_info,
            quantity=qty_val, unit=unit,
            purchase_price=purchase_val, purchase_date=purchase_date_val,
            sale_quantity=sale_qty_val,
            sale_price=sale_val, sale_date=sale_date_val,
            notes=notes,
        )
        messages.success(request, f'"{name}" envantere eklendi.')
    else:
        item.name           = name
        item.category       = category
        item.model_info     = model_info
        item.quantity       = qty_val
        item.unit           = unit
        item.purchase_price = purchase_val
        item.purchase_date  = purchase_date_val
        item.sale_quantity  = sale_qty_val
        item.sale_price     = sale_val
        item.sale_date      = sale_date_val
        item.notes          = notes
        item.save()
        saved = item
        messages.success(request, f'"{name}" güncellendi.')

    from transactions.models import Transaction as TxModel

    # Alış işlemi oluştur (cari/satıcı seçildiyse ve henüz bağlı işlem yoksa)
    if purchase_customer_id and not saved.source_transaction_id:
        pur_customer = Customer.objects.filter(pk=purchase_customer_id, user=request.user).first()
        if pur_customer:
            unit_price_tx = (purchase_val / qty_val) if qty_val else purchase_val
            purchase_tx = TxModel.objects.create(
                user=request.user,
                customer=pur_customer,
                type='purchase',
                product='diger',
                quantity=qty_val,
                unit=unit,
                unit_price=unit_price_tx,
                description=f'Envanter Alışı: {name}',
            )
            saved.source_transaction = purchase_tx
            saved.save(update_fields=['source_transaction'])
            messages.info(request, f'"{pur_customer.name}" cari hesabına alış işlemi oluşturuldu.')

    # Satış işlemi oluştur (cari/alıcı seçildiyse ve satış fiyatı varsa)
    if sale_customer_id and sale_val is not None and not saved.sale_transaction_id:
        sale_customer = Customer.objects.filter(pk=sale_customer_id, user=request.user).first()
        if sale_customer:
            effective_qty = sale_qty_val if sale_qty_val is not None else qty_val
            unit_price_tx = (sale_val / effective_qty) if effective_qty else sale_val
            sale_tx = TxModel.objects.create(
                user=request.user,
                customer=sale_customer,
                type='sale',
                product='diger',
                quantity=effective_qty,
                unit=unit,
                unit_price=unit_price_tx,
                description=f'Envanter Satışı: {name}',
            )
            saved.sale_transaction = sale_tx
            saved.save(update_fields=['sale_transaction'])
            messages.info(request, f'"{sale_customer.name}" cari hesabına satış işlemi oluşturuldu.')

    return redirect('inventory_list')
