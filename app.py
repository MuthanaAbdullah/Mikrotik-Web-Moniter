import time
import streamlit as _st
import routeros_api
import pandas as _pd
import plotly.express as _px

_st.set_page_config(
    page_title="مراقب ترافيك البرودباند الفني",
    page_icon="📡",
    layout="wide"
)

# --- تنسيق CSS لتوسيط الصفحة بعرض مناسب ومثالي ---
_st.markdown(
    """
    <style>
        .block-container {
            max-width: 850px;
            padding-top: 2rem;
            padding-bottom: 2rem;
            margin: auto;
            direction: rtl;
        }
        .search-box-container {
            background-color: #f8f9fa;
            padding: 22px;
            border-radius: 14px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 25px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

MIKROTIK_IP = "193.43.159.102"
MIKROTIK_USER = "MoniterinG-App"
MIKROTIK_PASS = "Tulipmm@2019"
MIKROTIK_PORT = 2773

def decode_arabic(text):
    if not text:
        return ""
    try:
        if '\\x' in text:
            clean_text = text.encode('ascii').decode('unicode-escape')
            return clean_text.encode('latin1').decode('cp1256')
        return text.encode('latin1').decode('cp1256')
    except Exception:
        return text

def format_rate(bps_val):
    try:
        bps = float(bps_val)
        if bps < 1000:
            return f"{int(bps)} bps"
        elif bps < 1000 * 1000:
            return f"{bps / 1000:.1f} Kbps"
        else:
            return f"{bps / (1000 * 1000):.2f} Mbps"
    except Exception:
        return "0 Kbps"

_st.markdown("<h1 style='text-align: center;'>📡 لوحة استعلام الدعم الفني للبرودباند</h1>", unsafe_allow_html=True)

# النص الإرشادي في المستطيل مباشرة أسفل عنوان لوحة استعلام الدعم الفني
_st.markdown(
    """
    <div style="background-color: #f8f9fa; padding: 12px 18px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; text-align: center; direction: rtl;">
        <span style="color: #495057; font-size: 0.95rem; font-weight: 500;">💡 يرجى كتابة اسم المشترك أو جزء من الكومنت في خانة البحث أعلاه لبدء الاستعلام ومراقبة الترافيك الحي.</span>
    </div>
    """,
    unsafe_allow_html=True
)

_st.markdown("---")

# صندوق البحث
with _st.container():
    _st.markdown('<div class="search-box-container">', unsafe_allow_html=True)
    col_search, col_toggle = _st.columns([2, 1])
    
    with col_search:
        search_query = _st.text_input("🔍 ابحث باسم المشترك أو الكومنت العربي:", placeholder="اكتب للبحث عن مشترك معين...")

    with col_toggle:
        _st.markdown("<br>", unsafe_allow_html=True)
        auto_refresh = _st.checkbox("🔄 مراقبة حية تلقائية", value=False)
    
    _st.markdown('</div>', unsafe_allow_html=True)

refresh_interval = 3

if not search_query.strip():
    if 'traffic_history' in _st.session_state:
        del _st.session_state['traffic_history']
else:
    placeholder = _st.empty()
    
    while True:
        with placeholder.container():
            try:
                connection = routeros_api.RouterOsApiPool(
                    MIKROTIK_IP,
                    username=MIKROTIK_USER,
                    password=MIKROTIK_PASS,
                    port=MIKROTIK_PORT,
                    plaintext_login=True
                )
                api = connection.get_api()
                
                active_users = api.get_resource('/ppp/active').get()
                interface_resource = api.get_resource('/interface')
                interfaces_1 = interface_resource.get()
                
                # فترة انتظار لضمان أخذ قراءة زمنية دقيقة للعدادات
                time.sleep(1)
                
                interfaces_2 = interface_resource.get()
                connection.disconnect()
                
                filtered_results = []
                current_time_str = time.strftime("%H:%M:%S")
                latest_rx_val = 0.0
                latest_tx_val = 0.0
                
                if active_users:
                    map_1 = {inf.get('name'): inf for inf in interfaces_1}
                    map_2 = {inf.get('name'): inf for inf in interfaces_2}
                    
                    for user in active_users:
                        raw_comment = user.get('comment', '')
                        decoded_comment = decode_arabic(raw_comment)
                        username = user.get('name', '')
                        
                        if search_query.strip() in decoded_comment or search_query.strip() in username:
                            rx_bps = 0
                            tx_bps = 0
                            
                            iface_name = username
                            if iface_name not in map_1:
                                for name in map_1.keys():
                                    if username in name or name.endswith(username):
                                        iface_name = name
                                        break
                            
                            if iface_name in map_1 and iface_name in map_2:
                                try:
                                    bytes1_rx = int(map_1[iface_name].get('rx-byte', 0))
                                    bytes2_rx = int(map_2[iface_name].get('rx-byte', 0))
                                    bytes1_tx = int(map_1[iface_name].get('tx-byte', 0))
                                    bytes2_tx = int(map_2[iface_name].get('tx-byte', 0))
                                    
                                    # قسمة الفرق على 2 لتصحيح مشكلة التضاعف وضبط القراءة تماماً مثل المايكروتك
                                    rx_bps = max(0, ((bytes2_rx - bytes1_rx) * 8) / 2)
                                    tx_bps = max(0, ((bytes2_tx - bytes1_tx) * 8) / 2)
                                except Exception:
                                    pass

                            # تحويل القيمة إلى Mbps ثابتة للمخطط
                            latest_rx_val = round(rx_bps / (1000.0 * 1000.0), 3)
                            latest_tx_val = round(tx_bps / (1000.0 * 1000.0), 3)

                            filtered_results.append({
                                "اسم الحساب": username,
                                "العنوان (IP)": user.get('address', 'غير متوفر'),
                                "التحميل (RX Rate)": format_rate(rx_bps),
                                "الرفع (Tx Rate)": format_rate(tx_bps),
                                "وقت التشغيل": user.get('uptime', 'غير متوفر'),
                                "الكومنت": decoded_comment if decoded_comment else "لا يوجد كومنت"
                            })
                    
                    if filtered_results:
                        _st.success(f"تم العثور على {len(filtered_results)} نتيجة مطابقة (جارِ المراقبة الحية):")
                        
                        # --- عرض النتائج ببطاقات متوسّطة الحجم ---
                        for res in filtered_results:
                            with _st.container():
                                _st.markdown(
                                    f"""
                                    <div style="background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e0e0e0; border-right: 5px solid #007bff; box-shadow: 0 3px 10px rgba(0,0,0,0.04); margin-bottom: 14px; direction: rtl;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                            <div>
                                                <span style="font-size: 1.15rem; font-weight: bold; color: #2C3E50; margin-left: 10px;">👤 {res['اسم الحساب']}</span>
                                                <span style="display: inline-flex; align-items: center; background-color: #e6f4ea; color: #137333; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold;">
                                                    <span style="height: 8px; width: 8px; background-color: #34a853; border-radius: 50%; display: inline-block; margin-left: 5px;"></span>
                                                    متصل
                                                </span>
                                            </div>
                                            <span style="background-color: #e7f1ff; color: #007bff; padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: bold;">🌐 {res['العنوان (IP)']}</span>
                                        </div>
                                        <div style="background-color: #f8f9fa; padding: 10px 14px; border-radius: 6px; font-size: 0.95rem; color: #495057; margin-bottom: 12px;">
                                            💬 <b>الكومنت:</b> {res['الكومنت']}
                                        </div>
                                        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #6c757d; border-top: 1px solid #eee; padding-top: 10px;">
                                            <div>⬇️ <b>التحميل:</b> <span style="color: #28a745; font-weight: bold;">{res['التحميل (RX Rate)']}</span></div>
                                            <div>⬆️ <b>الرفع:</b> <span style="color: #dc3545; font-weight: bold;">{res['الرفع (Tx Rate)']}</span></div>
                                            <div>⏱️ <b>وقت التشغيل:</b> <span style="color: #333333; font-weight: bold;">{res['وقت التشغيل']}</span></div>
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                        
                        # --- إدارة سجل البيانات للخط المتحرك ---
                        if 'traffic_history' not in _st.session_state:
                            _st.session_state['traffic_history'] = _pd.DataFrame(columns=["الوقت", "التحميل RX", "الرفع TX"])
                        
                        new_row = _pd.DataFrame({"الوقت": [current_time_str], "التحميل RX": [latest_rx_val], "الرفع TX": [latest_tx_val]})
                        _st.session_state['traffic_history'] = _pd.concat([_st.session_state['traffic_history'], new_row], ignore_index=True)
                        
                        if len(_st.session_state['traffic_history']) > 20:
                            _st.session_state['traffic_history'] = _st.session_state['traffic_history'].iloc[-20:]
                        
                        _st.markdown("### 📈 مؤشر السرعة الحي (وحدة القياس الثابتة: Mbps - متطابق مع المايكروتك)")
                        
                        # استخدام مكتبة Plotly
                        fig = _px.line(
                            _st.session_state['traffic_history'],
                            x="الوقت",
                            y=["التحميل RX", "الرفع TX"],
                            labels={"value": "السرعة (Mbps)", "variable": "المؤشر", "الوقت": "الوقت الحالي"},
                            markers=True
                        )
                        
                        fig.update_traces(line=dict(width=3))
                        fig.update_layout(
                            legend_title_text='نوع الترافيك',
                            margin=dict(l=10, r=10, t=10, b=10),
                            height=350,
                            xaxis=dict(showgrid=True),
                            yaxis=dict(showgrid=True)
                        )
                        
                        # الألوان المحددة: التحميل (RX) أخضر، الرفع (TX) برتقالي
                        fig.for_each_trace(lambda t: t.update(line=dict(color="#28a745" if "RX" in t.name else "#fd7e14", width=3)))
                        
                        _st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        _st.warning("عذراً، لم يتم العثور على أي مشترك مطابق لكلمة البحث.")
                else:
                    _st.info("لا توجد جلسات برودباند نشطة حالياً على الراوتر.")
                    
            except Exception as e:
                _st.error(f"خطأ في الاتصال بالمايكروتك: {e}")

        if not auto_refresh:
            break
        
        time.sleep(refresh_interval)
        _st.rerun()