#!/usr/bin/env python3
"""
Audit all assortments: verify optimal products meet explicit requirements.
Uses the actual build_prompt() to check what the model will see,
then verifies truthfulness against product specs.

Also audits the per-assortment preference_language overrides.
"""
import sys, re, json
sys.path.insert(0, '.')
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES
from experiment.conditions import compute_utility_scores, get_optimal_product, build_prompt


def extract_requirements(system_prompt: str) -> list[str]:
    """Extract bullet-point requirements from a preference_explicit prompt."""
    reqs = []
    for line in system_prompt.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            reqs.append(line[2:])
    return reqs


def get_all_text(product: dict) -> str:
    """Combine all product text fields for keyword searching."""
    specs = product.get('specs', {})
    desc = product.get('description', '')
    name = product.get('name', '')
    return json.dumps(specs) + ' ' + desc + ' ' + name


def product_meets_req(product: dict, req_text: str) -> tuple:
    """
    Check if a product meets a single natural language requirement.
    Returns (passes, reason).
    """
    specs = product.get('specs', {})
    desc = product.get('description', '')
    price = product.get('price', 9999)
    req_lower = req_text.lower()
    all_text = get_all_text(product)
    all_text_lower = all_text.lower()

    # ── Brand-agnostic requirements (always pass) ──
    brand_keywords = ['brand', "don't care", "doesn't matter", 'irrelevant',
                      'any brand', 'genuinely', 'not a consideration',
                      "canon, sony", "sony, bose", "apple, samsung"]
    if any(kw in req_lower for kw in brand_keywords):
        return True, 'brand-agnostic req (always passes)'

    # ── Price: "Under $X" ──
    price_match = re.search(r'under\s*\$(\d+(?:,\d+)?)', req_lower)
    if price_match:
        max_price = float(price_match.group(1).replace(',', ''))
        if price < max_price:
            return True, f'${price} < ${max_price}'
        else:
            return False, f'${price} >= ${max_price}'

    # ── Battery: hours ──
    # Patterns: "at least X hours battery", "X+ hours battery", "X hours battery life",
    #           "at least X hours of battery life", "over X hours battery"
    bat_hr_patterns = [
        r'(?:at least|over|minimum)\s*(\d+)\s*hours?\s*(?:of\s*)?battery',
        r'(\d+)\+?\s*hours?\s*(?:of\s*)?battery\s*life',
        r'(?:at least|over|minimum)\s*(\d+)\s*hours?\s*(?:of\s*)?battery\s*life',
    ]
    for pat in bat_hr_patterns:
        m = re.search(pat, req_lower)
        if m:
            target = int(m.group(1))
            bat_spec = specs.get('battery', '')
            bat_h = re.search(r'(\d+)\s*hour', bat_spec)
            if not bat_h:
                bat_h = re.search(r'(\d+)\s*hr', bat_spec)
            if bat_h:
                actual = int(bat_h.group(1))
                if actual >= target:
                    return True, f'{actual}h >= {target}h'
                else:
                    return False, f'{actual}h < {target}h'
            # Check if spec has just a number like "18 hours" or "12 hours"
            bat_num = re.search(r'(\d+)', bat_spec)
            if bat_num and 'day' not in bat_spec.lower():
                actual = int(bat_num.group(1))
                if actual >= target:
                    return True, f'{actual}h >= {target}h (parsed from "{bat_spec}")'
                else:
                    return False, f'{actual}h < {target}h (parsed from "{bat_spec}")'
            if 'wired' in bat_spec.lower():
                return False, f'wired only (no battery)'
            return False, f'no battery hours found in spec: "{bat_spec}"'

    # ── Battery: days ──
    bat_day_patterns = [
        r'(?:at least|over|minimum)\s*(\d+)\s*days?\s*battery',
    ]
    for pat in bat_day_patterns:
        m = re.search(pat, req_lower)
        if m:
            target = int(m.group(1))
            bat_spec = specs.get('battery', '')
            day_m = re.search(r'(\d+)\s*day', bat_spec)
            if day_m:
                actual = int(day_m.group(1))
                if actual >= target:
                    return True, f'{actual}d >= {target}d'
                else:
                    return False, f'{actual}d < {target}d'
            # Check for month-based specs (e.g., "3 months" = 90 days)
            month_m = re.search(r'(\d+)\s*month', bat_spec)
            if month_m:
                actual_days = int(month_m.group(1)) * 30
                if actual_days >= target:
                    return True, f'{actual_days}d >= {target}d (from months)'
                else:
                    return False, f'{actual_days}d < {target}d (from months)'
            # Hours-based check: if battery is in hours and < 24, clearly fails "X days"
            hr_m = re.search(r'(\d+)\s*hour', bat_spec)
            if hr_m:
                actual_hrs = int(hr_m.group(1))
                actual_days = actual_hrs / 24
                if actual_days >= target:
                    return True, f'{actual_hrs}h = {actual_days:.1f}d >= {target}d'
                else:
                    return False, f'{actual_hrs}h = {actual_days:.1f}d < {target}d'
            return False, f'no battery days found in spec: "{bat_spec}"'

    # ── Display resolution: "2K or higher", "4K resolution", "2.8K or higher" ──
    res_patterns = [
        (r'2\.8k\s*or\s*higher', ['2.8K', '2.8k', '3K', '4K', '2880', '2800']),
        (r'2k\s*or\s*higher', ['2K', '2k', '2560', 'QHD', '2.8K', '4K', '3840']),
        (r'4k\s*resolution', ['4K', '4k', '3840', 'UHD']),
    ]
    for pat, keywords in res_patterns:
        if re.search(pat, req_lower):
            check_fields = [specs.get('display', ''), specs.get('resolution', ''), desc]
            for field in check_fields:
                for kw in keywords:
                    if kw in field:
                        return True, f'found "{kw}" for resolution'
            # If "FHD" or "1080" is the resolution, it's less than 2K
            for field in check_fields:
                if 'FHD' in field or '1080' in field or '1920' in field:
                    return False, f'FHD/1080p < required resolution'
                if 'HD' in field and '2K' not in field and '4K' not in field and 'QHD' not in field and 'UHD' not in field:
                    return False, f'HD < required resolution'
            return False, f'no matching resolution found'

    # ── RAM: "XGB RAM minimum" or "16GB RAM" ──
    ram_match = re.search(r'(\d+)gb\s*ram', req_lower)
    if ram_match:
        target = int(ram_match.group(1))
        ram_spec = specs.get('ram', '')
        ram_num = re.search(r'(\d+)\s*GB', ram_spec, re.IGNORECASE)
        if not ram_num:
            ram_num = re.search(r'(\d+)', ram_spec)
        if ram_num:
            actual = int(ram_num.group(1))
            if actual >= target:
                return True, f'{actual}GB >= {target}GB RAM'
            else:
                return False, f'{actual}GB < {target}GB RAM'
        return False, f'no RAM spec found: "{ram_spec}"'

    # ── Display/TV size: "At least X inches" or "X inches or larger" ──
    size_patterns = [
        r'(?:at least|minimum)\s*(\d+(?:\.\d+)?)\s*inch',
        r'(\d+(?:\.\d+)?)\s*inch(?:es)?\s*or\s*larger',
    ]
    for pat in size_patterns:
        m = re.search(pat, req_lower)
        if m:
            target = float(m.group(1))
            size_fields = [specs.get('size', ''), specs.get('display', ''), desc]
            for field in size_fields:
                size_m = re.search(r'(\d+(?:\.\d+)?)["\']?\s*(?:inch|")', field)
                if not size_m:
                    size_m = re.search(r'(\d+(?:\.\d+)?)"', field)
                if size_m:
                    actual = float(size_m.group(1))
                    if actual >= target:
                        return True, f'{actual}" >= {target}"'
                    else:
                        return False, f'{actual}" < {target}"'
            return False, f'no size found in specs'

    # ── Panel type: "QLED or OLED panel" ──
    if 'qled or oled' in req_lower:
        panel = specs.get('panel', '') + ' ' + desc
        if any(kw in panel for kw in ['QLED', 'OLED', 'Neo QLED', 'OLED evo']):
            return True, f'panel matches QLED/OLED'
        else:
            return False, f'panel is "{specs.get("panel", "")}" (not QLED/OLED)'

    # ── Suction (Pa): "at least XPa" ──
    suction_match = re.search(r'(?:at least|minimum)\s*(\d+)\s*pa\s*suction', req_lower)
    if suction_match:
        target = int(suction_match.group(1))
        suction_spec = specs.get('suction', '')
        s_num = re.search(r'(\d+)\s*Pa', suction_spec)
        if s_num:
            actual = int(s_num.group(1))
            if actual >= target:
                return True, f'{actual}Pa >= {target}Pa'
            else:
                return False, f'{actual}Pa < {target}Pa'
        # Non-Pa units (e.g., "65 AW")
        if 'AW' in suction_spec or suction_spec == '':
            return False, f'no Pa suction: "{suction_spec}"'

    # ── Speed: "at least XMB/s read speed" ──
    speed_match = re.search(r'(?:at least|minimum)\s*(\d+)\s*mb/s', req_lower)
    if speed_match:
        target = int(speed_match.group(1))
        speed_spec = specs.get('speed', '')
        s_num = re.search(r'(\d+)\s*MB/s', speed_spec)
        if s_num:
            actual = int(s_num.group(1))
            if actual >= target:
                return True, f'{actual}MB/s >= {target}MB/s'
            else:
                return False, f'{actual}MB/s < {target}MB/s'
        return False, f'no speed spec: "{speed_spec}"'

    # ── Wattage: "at least X watts" or "XW or higher motor" ──
    watt_patterns = [
        r'(?:at least|minimum)\s*(\d+)\s*watt',
        r'(\d+)w\s*or\s*higher',
    ]
    for pat in watt_patterns:
        m = re.search(pat, req_lower)
        if m:
            target = int(m.group(1))
            power_spec = specs.get('power', '')
            p_num = re.search(r'(\d+)\s*W', power_spec)
            if p_num:
                actual = int(p_num.group(1))
                if actual >= target:
                    return True, f'{actual}W >= {target}W'
                else:
                    return False, f'{actual}W < {target}W'
            return False, f'no wattage found: "{power_spec}"'

    # ── Coverage: "at least X sq ft" ──
    cov_match = re.search(r'(?:at least|minimum)\s*(\d+)\s*sq\s*ft', req_lower)
    if cov_match:
        target = int(cov_match.group(1))
        cov_spec = specs.get('coverage', '')
        c_num = re.search(r'(\d+)\s*sq\s*ft', cov_spec)
        if c_num:
            actual = int(c_num.group(1))
            if actual >= target:
                return True, f'{actual} sq ft >= {target} sq ft'
            else:
                return False, f'{actual} sq ft < {target} sq ft'
        return False, f'no coverage: "{cov_spec}"'

    # ── Megapixels: "at least XMP sensor" ──
    mp_match = re.search(r'(?:at least|minimum)\s*(\d+)\s*mp', req_lower)
    if mp_match:
        target = int(mp_match.group(1))
        sensor_spec = specs.get('sensor', '') + ' ' + specs.get('camera', '')
        mp_num = re.search(r'(\d+(?:\.\d+)?)\s*MP', sensor_spec)
        if mp_num:
            actual = float(mp_num.group(1))
            if actual >= target:
                return True, f'{actual}MP >= {target}MP'
            else:
                return False, f'{actual}MP < {target}MP'
        return False, f'no MP found: "{sensor_spec}"'

    # ── Refresh rate: "120Hz or higher" / "144Hz" ──
    refresh_match = re.search(r'(\d+)\s*hz\s*(?:or\s*higher|(?:refresh|display))', req_lower)
    if not refresh_match:
        refresh_match = re.search(r'(\d+)\s*hz\s*or\s*higher', req_lower)
    if refresh_match:
        target = int(refresh_match.group(1))
        refresh_spec = specs.get('refresh', '') + ' ' + specs.get('display', '')
        r_num = re.search(r'(\d+)\s*Hz', refresh_spec)
        if r_num:
            actual = int(r_num.group(1))
            if actual >= target:
                return True, f'{actual}Hz >= {target}Hz'
            else:
                return False, f'{actual}Hz < {target}Hz'
        return False, f'no refresh rate: "{refresh_spec}"'

    # ── Capacity range: "20-25L" ──
    cap_range_match = re.search(r'(\d+)\s*-\s*(\d+)\s*l\s*capacity', req_lower)
    if cap_range_match:
        lo = int(cap_range_match.group(1))
        hi = int(cap_range_match.group(2))
        cap_spec = specs.get('capacity', '')
        c_num = re.search(r'(\d+)\s*L', cap_spec)
        if c_num:
            actual = int(c_num.group(1))
            if lo <= actual <= hi:
                return True, f'{actual}L in [{lo}-{hi}L]'
            else:
                return False, f'{actual}L not in [{lo}-{hi}L]'
        return False, f'no capacity: "{cap_spec}"'

    # ── Temperature range: "195-205F" or "brews at 195-205F" ──
    temp_match = re.search(r'(\d+)\s*-\s*(\d+)\s*f', req_lower)
    if temp_match:
        lo_temp = int(temp_match.group(1))
        hi_temp = int(temp_match.group(2))
        brew_spec = specs.get('brew_temp', '')
        # Check for exact range match
        t_nums = re.findall(r'(\d+)', brew_spec)
        if t_nums:
            temps = [int(x) for x in t_nums]
            # Check if spec range overlaps or fits within required range
            if any(lo_temp <= t <= hi_temp for t in temps):
                return True, f'brew temp {brew_spec} within {lo_temp}-{hi_temp}F'
            else:
                return False, f'brew temp {brew_spec} outside {lo_temp}-{hi_temp}F'
        return False, f'no temp found: "{brew_spec}"'

    # ── Weight for shoes (grams) ──
    weight_g_match = re.search(r'under\s*(\d+)\s*g\b', req_lower)
    if weight_g_match:
        target_g = int(weight_g_match.group(1))
        wt_spec = specs.get('weight', '')
        wt_g = re.search(r'(\d+)\s*g\b', wt_spec)
        if wt_g:
            actual = int(wt_g.group(1))
            if actual < target_g:
                return True, f'{actual}g < {target_g}g'
            else:
                return False, f'{actual}g >= {target_g}g'

    # ── Under 400g body weight ──
    weight_body_match = re.search(r'under\s*(\d+)\s*g\s*body\s*weight', req_lower)
    if weight_body_match:
        target_g = int(weight_body_match.group(1))
        wt_spec = specs.get('weight', '')
        wt_g = re.search(r'(\d+)\s*g', wt_spec)
        if wt_g:
            actual = int(wt_g.group(1))
            if actual < target_g:
                return True, f'{actual}g < {target_g}g'
            else:
                return False, f'{actual}g >= {target_g}g'

    # ── Weight for portable items (pounds) ──
    if 'under 1 pound' in req_lower:
        wt_spec = specs.get('weight', '')
        oz_match = re.search(r'(\d+\.?\d*)\s*oz', wt_spec)
        lb_match = re.search(r'(\d+\.?\d*)\s*lb', wt_spec)
        if oz_match and float(oz_match.group(1)) < 16:
            return True, f'{oz_match.group(1)}oz < 16oz'
        elif lb_match and float(lb_match.group(1)) >= 1:
            return False, f'{lb_match.group(1)}lbs >= 1lb'
        elif oz_match:
            return False, f'{oz_match.group(1)}oz >= 16oz'

    # ── Playback hours for earbuds ──
    playback_hrs = re.search(r'(\d+)\s*hours?\s*playback', req_lower)
    if playback_hrs:
        target = int(playback_hrs.group(1))
        bat_spec = specs.get('battery', '')
        bat_h = re.search(r'(\d+\.?\d*)h', bat_spec)
        if bat_h:
            actual = float(bat_h.group(1))
            if actual >= target:
                return True, f'{actual}h >= {target}h'
            else:
                return False, f'{actual}h < {target}h'

    # ── 50MP camera ──
    if '50mp' in req_lower and 'camera' in req_lower:
        cam = specs.get('camera', '')
        cam_mp = re.search(r'(\d+)MP', cam)
        if cam_mp and int(cam_mp.group(1)) >= 50:
            return True, f'{cam_mp.group(1)}MP >= 50MP'
        elif cam_mp:
            return False, f'{cam_mp.group(1)}MP < 50MP'

    # ── Storage: "256GB storage minimum" ──
    stor_match = re.search(r'(\d+)\s*gb\s*storage', req_lower)
    if stor_match:
        target = int(stor_match.group(1))
        stor = specs.get('storage', '')
        stor_gb = re.search(r'(\d+)', stor)
        if stor_gb and int(stor_gb.group(1)) >= target:
            return True, f'{stor_gb.group(1)}GB >= {target}GB'
        elif stor_gb:
            return False, f'{stor_gb.group(1)}GB < {target}GB'

    # ── mAh battery ──
    mah_match = re.search(r'(\d+)\s*mah', req_lower)
    if mah_match:
        target = int(mah_match.group(1))
        bat = specs.get('battery', '')
        bat_mah = re.search(r'(\d+)\s*mAh', bat)
        if bat_mah and int(bat_mah.group(1)) >= target:
            return True, f'{bat_mah.group(1)}mAh >= {target}mAh'
        elif bat_mah:
            return False, f'{bat_mah.group(1)}mAh < {target}mAh'

    # ── Power output: "XW output" or "XW+ output" ──
    power_out_match = re.search(r'(\d+)\s*w\+?\s*output', req_lower)
    if power_out_match:
        target = int(power_out_match.group(1))
        power = specs.get('power', '')
        power_w = re.search(r'(\d+)\s*W', power)
        if power_w and int(power_w.group(1)) >= target:
            return True, f'{power_w.group(1)}W >= {target}W'
        elif power_w:
            return False, f'{power_w.group(1)}W < {target}W'
        elif 'N/A' in power:
            return False, f'power N/A'

    # ── Impedance ──
    impedance_match = re.search(r'under\s*(\d+)\s*ohm', req_lower)
    if impedance_match:
        target = int(impedance_match.group(1))
        imp = specs.get('impedance', '')
        imp_val = re.search(r'(\d+)', imp)
        if imp_val and int(imp_val.group(1)) < target:
            return True, f'{imp_val.group(1)} ohm < {target} ohm'
        elif imp_val:
            return False, f'{imp_val.group(1)} ohm >= {target} ohm'

    # ── Nits brightness: "at least X nits" or "2000 nits" ──
    nits_match = re.search(r'(?:at least|minimum|over)\s*(\d+)\s*nits', req_lower)
    if nits_match:
        target = int(nits_match.group(1))
        brightness_spec = specs.get('brightness', '')
        desc_for_nits = brightness_spec + ' ' + desc
        n_match = re.search(r'(\d+)\s*nits', desc_for_nits)
        if n_match:
            actual = int(n_match.group(1))
            if actual >= target:
                return True, f'{actual} nits >= {target} nits'
            else:
                return False, f'{actual} nits < {target} nits'
        return False, f'no nits spec found'

    # ── Keyword-based checks ──
    # Each entry: trigger keyword in req → list of positive keywords to find in product data,
    #             and optionally a list of negative keywords that mean FAIL
    keyword_checks = {
        # Phones
        'modular': (['modular'], []),
        'user-repair': (['modular', 'repairable', 'replaceable'], []),
        '8+ years': (['8+ years', '8 years'], []),
        'ethically sourced': (['ethically sourced', 'fair trade', 'ethical'], []),
        # Shoes
        'graphene': (['graphene'], []),
        'all-terrain': (['all trail', 'all-terrain'], []),
        'carbon fiber': (['carbon'], []),
        # Headphones
        'planar magnetic': (['planar magnetic'], []),
        'open-back': (['open-back'], []),
        'over-ear': (['over-ear'], []),
        'ldac': (['LDAC', 'ldac'], []),
        'aptx adaptive': (['aptX Adaptive', 'aptx adaptive'], []),
        # Earbuds
        'open-ear': (['open-ear', 'ear-hook', 'open ear'], []),
        'ipx8': (['IPX8', 'ipx8'], []),
        'ipx5': (['IPX5', 'ipx5', 'IPX6', 'IPX7', 'IPX8', 'IP67', 'IP68'], []),
        'ip67': (['IP67', 'ip67', 'IP68', 'IPX7', 'IPX8'], []),
        # Coffee
        'manual lever': (['manual lever'], []),
        'pressure profiling': (['pressure profil', '6-9 bar'], []),
        'no electricity': (['no electricity', 'manual espresso', 'manual press', 'french press'], []),
        'pocket-sized': (['pocket', 'compact'], []),
        '15+ bar': (['18 bar', '15 bar', '16 bar', '17 bar', '19 bar', '20 bar'], []),
        'pre-infusion': (['pre-infusion', 'pre_infusion', 'bloom'], []),
        'thermal carafe': (['thermal', 'stainless steel thermal'], []),
        'sca certified': (['SCA', 'sca_certified'], []),
        # TVs
        'mini-led': (['Mini-LED', 'mini-led', 'Mini LED', 'Mini-LED'], []),
        '1000+ local dimming': (['1500+', '1000+', '1152'], []),
        'dolby vision': (['Dolby Vision', 'dolby vision'], []),
        'hdr10+': (['HDR10+', 'hdr10+'], []),
        'hdr1000': (['HDR1000', 'hdr1000', 'HDR 1000'], []),
        # Speakers
        '36+ hours': (['36hr', '36 hr', '36 hour', '48hr'], []),
        'stainless steel': (['stainless'], []),
        '32oz': (['32oz', '32 oz'], []),
        # ANC
        '-45db': (['-45dB', '-50dB', '-46dB', '-47dB', '-48dB', '-49dB',
                   '45dB', '50dB', '42dB'], []),
        # Smartwatches
        'multi-band': (['multi-band', 'dual-band', 'multi band', 'dual band'], []),
        'always-on': (['always-on', 'Always-on', 'always on'], []),
        'amoled': (['AMOLED', 'amoled'], []),
        # Robot vacuums
        'lidar': (['LiDAR', 'lidar', 'LIDAR'], []),
        'self-emptying': (['self-empty', 'auto-empty', 'auto empty', 'self-wash'], []),
        # Keyboards
        'hot-swap': (['hot-swap', 'hot swap', 'Hot-swap'], []),
        'gasket': (['gasket', 'Gasket'], []),
        'pbt': (['PBT', 'pbt'], []),
        # External SSDs
        '2tb': (['2TB', '2 TB'], []),
        'ip55': (['IP55', 'ip55', 'IP65', 'IP67', 'IP68', 'MIL-STD'], []),
        # Electric toothbrushes
        'sonic': (['sonic', 'Sonic'], []),
        'pressure sensor': (['pressure_sensor', 'pressure sensor'], []),
        'timer': (['timer', 'Timer', '2-min'], []),
        # Backpacks
        'cordura': (['CORDURA', 'Cordura', 'cordura'], []),
        'laptop compartment': (['laptop', 'Laptop'], []),
        # Blenders
        'bpa-free': (['BPA-free', 'bpa_free', 'BPA free'], []),
        'variable speed': (['variable', 'Variable'], []),
        'continuously variable': (['variable + pulse', 'variable 1-10', 'variable speed'], []),
        # Routers
        'wifi 6e': (['WiFi 6E', 'wifi 6e', 'Wi-Fi 6E'], []),
        'wifi 7': (['WiFi 7', 'wifi 7', 'Wi-Fi 7'], []),
        'wpa3': (['WPA3', 'wpa3'], []),
        # Monitors
        'ips panel': (['IPS', 'ips'], []),
        'srgb': (['sRGB', 'DCI-P3'], []),
        'dci-p3': (['DCI-P3', 'dci-p3'], []),
        'height-adjustable': (['height', 'Height'], []),
        # Tablets
        'stylus': (['stylus', 'Stylus', 'Pencil', 'S Pen', 'pen included', 'stylus support'], []),
        # Cameras
        'ibis': (['IBIS', 'ibis', '5-axis', 'in-body'], []),
        'image stabilization': (['IBIS', 'ibis', '5-axis', 'in-body image stabilization'], []),
        'weather-sealed': (['weather sealed', 'Weather sealed', 'IP53', 'weather-sealed',
                            'dust and moisture'], []),
    }

    for keyword, (pos_keywords, neg_keywords) in keyword_checks.items():
        if keyword in req_lower:
            for dk in pos_keywords:
                # Case-sensitive check first, then case-insensitive
                if dk in all_text or dk.lower() in all_text_lower:
                    return True, f'found "{dk}" in product data'
            # Check boolean spec fields
            for key, val in specs.items():
                if val is True and keyword in key.lower():
                    return True, f'specs.{key} = True'
            return False, f'"{keyword}" not found in product data'

    # ── Laptop compartment size: "up to 16 inch" ──
    laptop_size_match = re.search(r'laptop.*(?:up to|at least)\s*(\d+)\s*inch', req_lower)
    if laptop_size_match:
        target = int(laptop_size_match.group(1))
        laptop_spec = specs.get('laptop', '')
        l_num = re.search(r'(\d+)', laptop_spec)
        if l_num:
            actual = int(l_num.group(1))
            if actual >= target:
                return True, f'{actual}" laptop >= {target}"'
            else:
                return False, f'{actual}" laptop < {target}"'

    # ── Sonic strokes/min: "30,000+" ──
    strokes_match = re.search(r'(\d+),?(\d+)\+?\s*strokes', req_lower)
    if strokes_match:
        target = int(strokes_match.group(1) + strokes_match.group(2))
        strokes_spec = specs.get('strokes', '')
        s_match = re.search(r'(\d+),?(\d+)', strokes_spec)
        if s_match:
            actual = int(s_match.group(1) + s_match.group(2))
            if actual >= target:
                return True, f'{actual} strokes/min >= {target}'
            else:
                return False, f'{actual} strokes/min < {target}'
        # Check for "N/A (oscillating)" type
        if 'oscillating' in strokes_spec.lower() or 'rotation' in strokes_spec.lower():
            return False, f'not sonic: "{strokes_spec}"'

    # ── Capacity (oz): "64oz+" or "64oz or larger" ──
    oz_cap_match = re.search(r'(\d+)\s*oz\+?\s*', req_lower)
    if oz_cap_match and 'pitcher' in req_lower:
        target = int(oz_cap_match.group(1))
        cap_spec = specs.get('capacity', '')
        c_num = re.search(r'(\d+)\s*oz', cap_spec)
        if c_num:
            actual = int(c_num.group(1))
            if actual >= target:
                return True, f'{actual}oz >= {target}oz'
            else:
                return False, f'{actual}oz < {target}oz'

    # ── Combined requirements with commas (e.g., "4K resolution, 55 inches or larger") ──
    # Split on comma and check each part
    if ',' in req_text and not any(kw in req_lower for kw in ['brand', "don't care"]):
        parts = [p.strip() for p in req_text.split(',')]
        all_parts_pass = True
        reasons = []
        for part in parts:
            part_pass, part_reason = product_meets_req(product, part)
            reasons.append(f'{part[:30]}={part_pass}')
            if part_pass is False:
                all_parts_pass = False
        if not all_parts_pass:
            return False, f'combined: {"; ".join(reasons)}'
        if all(r.endswith('=True') for r in reasons):
            return True, f'combined: {"; ".join(reasons)}'

    # ── "BOTH X AND Y" requirements ──
    both_match = re.search(r'both\s+(.+?)\s+and\s+(.+)', req_lower)
    if both_match:
        part1 = both_match.group(1).strip()
        part2 = both_match.group(2).strip()
        # Check both in all_text
        hdr_spec = specs.get('hdr', '')
        p1_found = any(kw in all_text for kw in [part1.title(), part1.upper()])
        p2_found = any(kw in all_text for kw in [part2.upper(), part2.title()])
        # Special handling for HDR formats
        if 'dolby vision' in part1:
            p1_found = 'Dolby Vision' in hdr_spec or 'dolby vision' in hdr_spec.lower()
        if 'hdr10+' in part2:
            p2_found = 'HDR10+' in hdr_spec
        if p1_found and p2_found:
            return True, f'both found in product data'
        elif not p1_found and not p2_found:
            return False, f'neither "{part1}" nor "{part2}" found'
        elif not p1_found:
            return False, f'"{part1}" not found'
        else:
            return False, f'"{part2}" not found'

    return None, f'could not parse: "{req_text[:60]}"'


print('=' * 100)
print('COMPREHENSIVE ASSORTMENT AUDIT')
print('Checking ACTUAL generated prompts against ACTUAL product specs')
print('=' * 100)

total_reqs = 0
verified_pass = 0
verified_fail = 0
unverifiable = 0
assortment_status = {}

for assortment in ALL_ASSORTMENTS:
    aid = assortment['id']
    scores = compute_utility_scores(assortment)
    opt_letter, opt_score = get_optimal_product(assortment, scores)

    opt_prod = None
    for p in assortment['products']:
        if p['letter'] == opt_letter:
            opt_prod = p
            break

    # Generate actual prompt
    sys_prompt, user_msg, meta = build_prompt(
        assortment, 'preference_explicit',
        category_preferences=CATEGORY_PREFERENCES,
        paraphrase_index=0,
        shuffle_products=False,
    )

    # Extract requirements
    reqs = extract_requirements(sys_prompt)
    if not reqs:
        print(f'\n  WARN  {aid}: No bullet requirements found in prompt')
        continue

    # Check optimal product against each requirement
    all_pass = True
    req_results = []
    for req in reqs:
        total_reqs += 1
        passes, reason = product_meets_req(opt_prod, req)
        req_results.append((req, passes, reason))
        if passes is True:
            verified_pass += 1
        elif passes is False:
            verified_fail += 1
            all_pass = False
        else:
            unverifiable += 1

    # Check non-optimal products (do any pass ALL requirements?)
    competitors_passing = []
    for p in assortment['products']:
        if p['letter'] == opt_letter:
            continue
        p_all_pass = True
        for req in reqs:
            passes, _ = product_meets_req(p, req)
            if passes is False:
                p_all_pass = False
                break
        if p_all_pass:
            competitors_passing.append(p['letter'])

    status = 'PASS' if all_pass else 'FAIL'
    if competitors_passing:
        status = 'WARN'
    assortment_status[aid] = status

    if status != 'PASS':
        print(f'\n  {status}  {aid} (optimal={opt_letter}: {opt_prod["name"]})')
        for req, passes, reason in req_results:
            icon = '  V' if passes else (' X' if passes is False else ' ?')
            print(f'       {icon} {req[:70]} -- {reason}')
        if competitors_passing:
            print(f'       ** Competitors also passing: {competitors_passing}')
    else:
        print(f'  PASS  {aid} (optimal={opt_letter})')

# Summary
n_pass = sum(1 for s in assortment_status.values() if s == 'PASS')
n_fail = sum(1 for s in assortment_status.values() if s == 'FAIL')
n_warn = sum(1 for s in assortment_status.values() if s == 'WARN')

print(f'\n{"=" * 100}')
print(f'AUDIT SUMMARY')
print(f'{"=" * 100}')
print(f'Assortments: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL (total: {len(assortment_status)})')
print(f'Requirements: {verified_pass} verified pass, {verified_fail} verified fail, {unverifiable} unverifiable (total: {total_reqs})')

if n_fail > 0:
    print(f'\nFAILING:')
    for aid, status in assortment_status.items():
        if status == 'FAIL':
            print(f'  {aid}')

if n_warn > 0:
    print(f'\nWARNINGS (competitors also pass):')
    for aid, status in assortment_status.items():
        if status == 'WARN':
            print(f'  {aid}')
