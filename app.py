import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps
from database import (db, init_db, USE_POSTGRES, _p, count, last_insert_id,
    get_settings, get_pages, get_page_by_slug, get_page_by_id,
    get_home_page, get_sections, get_nav, get_socials,
    get_initiatives, get_all_initiatives)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clinton-tech-dev-suite-2024-secret')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'ico', 'svg'}

def _safe_float(v, default=0.0):
    try: return float(v or 0)
    except: return default

def _safe_int(v, default=0):
    try: return int(v or 0)
    except: return default

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'clinton2024')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── THEMES ──────────────────────────────────────────────────────────────────
THEMES = [
    {"id": "minimal-edge",  "name": "Minimal Edge",    "desc": "Ultra-clean, sharp lines"},
    {"id": "bold-studio",   "name": "Bold Studio",     "desc": "High-contrast creative agency"},
    {"id": "classic-pro",   "name": "Classic Pro",     "desc": "Traditional corporate elegance"},
    {"id": "neon-future",   "name": "Neon Future",     "desc": "Dark with vivid neon accents"},
    {"id": "organic-warm",  "name": "Organic Warm",    "desc": "Natural textures, soft tones"},
    {"id": "magazine",      "name": "Magazine",        "desc": "Editorial-style large typography"},
    {"id": "glass-dark",    "name": "Glass Dark",      "desc": "Glassmorphism on dark bg"},
    {"id": "retro-grid",    "name": "Retro Grid",      "desc": "80s-inspired grid aesthetic"},
    {"id": "brutalist",     "name": "Brutalist",       "desc": "Raw, bold, unapologetic"},
    {"id": "swiss-clean",   "name": "Swiss Clean",     "desc": "Grid-based Swiss design"},
    {"id": "luxury-gold",   "name": "Luxury Gold",     "desc": "Premium dark gold aesthetic"},
    {"id": "pastel-soft",   "name": "Pastel Soft",     "desc": "Gentle pastel gradients"},
    {"id": "tech-dark",     "name": "Tech Dark",       "desc": "Developer-focused dark theme"},
    {"id": "earthy-sage",   "name": "Earthy Sage",     "desc": "Muted greens and taupes"},
    {"id": "midnight-blue", "name": "Midnight Blue",   "desc": "Deep navy professional"},
    {"id": "coral-pop",     "name": "Coral Pop",       "desc": "Energetic warm coral tones"},
    {"id": "monochrome",    "name": "Monochrome",      "desc": "Black, white, grey only"},
    {"id": "forest-deep",   "name": "Forest Deep",     "desc": "Rich forest greens"},
    {"id": "sunset-grad",   "name": "Sunset Gradient", "desc": "Warm gradient flows"},
    {"id": "arctic-white",  "name": "Arctic White",    "desc": "Crisp white minimal"},
    {"id": "cinematic",     "name": "Cinematic",       "desc": "Film-noir dramatic contrast"},
    {"id": "playful-bold",  "name": "Playful Bold",    "desc": "Fun, rounded, colorful"},
]

COLOR_SCHEMES = [
    {"id":"crimson-black",   "name":"Crimson Black",   "primary":"#DC143C","secondary":"#1a1a1a","accent":"#FF4444","bg":"#0d0d0d","text":"#f0f0f0"},
    {"id":"ocean-blue",      "name":"Ocean Blue",      "primary":"#0077B6","secondary":"#023E8A","accent":"#00B4D8","bg":"#f0f8ff","text":"#1a1a2e"},
    {"id":"forest-green",    "name":"Forest Green",    "primary":"#2D6A4F","secondary":"#1B4332","accent":"#74C69D","bg":"#f8fdf9","text":"#1a2e1f"},
    {"id":"purple-haze",     "name":"Purple Haze",     "primary":"#7B2FBE","secondary":"#3A0CA3","accent":"#C77DFF","bg":"#0d0d1a","text":"#e8e0ff"},
    {"id":"midnight-gold",   "name":"Midnight Gold",   "primary":"#C9A84C","secondary":"#8B6914","accent":"#FFD700","bg":"#0a0a0a","text":"#f5f0e0"},
    {"id":"coral-sunset",    "name":"Coral Sunset",    "primary":"#FF6B6B","secondary":"#C62828","accent":"#FFD166","bg":"#fff9f5","text":"#2d1515"},
    {"id":"slate-tech",      "name":"Slate Tech",      "primary":"#334155","secondary":"#1E293B","accent":"#38BDF8","bg":"#f8fafc","text":"#0f172a"},
    {"id":"rose-gold",       "name":"Rose Gold",       "primary":"#B5616A","secondary":"#8B3A42","accent":"#F4A2A2","bg":"#fdf5f5","text":"#2d1010"},
    {"id":"neon-lime",       "name":"Neon Lime",       "primary":"#ADFF2F","secondary":"#7CFC00","accent":"#00FF7F","bg":"#0a0a0a","text":"#f0f0f0"},
    {"id":"burnt-orange",    "name":"Burnt Orange",    "primary":"#CC5500","secondary":"#8B3A00","accent":"#FF8C42","bg":"#fdf5ee","text":"#1a0a00"},
    {"id":"icy-mint",        "name":"Icy Mint",        "primary":"#3CAEA3","secondary":"#20736A","accent":"#A8E6CF","bg":"#f0fffa","text":"#0a2e2a"},
    {"id":"plum-wine",       "name":"Plum Wine",       "primary":"#6B2D5E","secondary":"#3D1A35","accent":"#D4A0C7","bg":"#0d0008","text":"#f0e8ef"},
    {"id":"steel-blue",      "name":"Steel Blue",      "primary":"#4682B4","secondary":"#2C5F8A","accent":"#87CEEB","bg":"#f5f8fc","text":"#0d1f35"},
    {"id":"charcoal-red",    "name":"Charcoal Red",    "primary":"#E53935","secondary":"#B71C1C","accent":"#FF8A80","bg":"#1a1a1a","text":"#f5f5f5"},
    {"id":"sage-stone",      "name":"Sage Stone",      "primary":"#8FAF8A","secondary":"#5A7A55","accent":"#C8D8C0","bg":"#f5f5f0","text":"#2a352a"},
    {"id":"ink-blue",        "name":"Ink Blue",        "primary":"#1A237E","secondary":"#0D47A1","accent":"#42A5F5","bg":"#f5f7ff","text":"#0a0d2e"},
    {"id":"terracotta",      "name":"Terracotta",      "primary":"#C06C4A","secondary":"#8B4513","accent":"#E8A87C","bg":"#fdf5f0","text":"#2e1510"},
    {"id":"arctic-teal",     "name":"Arctic Teal",     "primary":"#008080","secondary":"#004D4D","accent":"#00CED1","bg":"#f0fffe","text":"#001a1a"},
    {"id":"warm-cream",      "name":"Warm Cream",      "primary":"#8B7355","secondary":"#5C4A2A","accent":"#D4A853","bg":"#faf8f3","text":"#2a1f0d"},
    {"id":"electric-violet", "name":"Electric Violet", "primary":"#8B00FF","secondary":"#5A0099","accent":"#DA70D6","bg":"#0a0015","text":"#f0e8ff"},
    {"id":"deep-maroon",     "name":"Deep Maroon",     "primary":"#800000","secondary":"#4A0000","accent":"#CD5C5C","bg":"#fdf5f5","text":"#1a0000"},
    {"id":"fresh-lime",      "name":"Fresh Lime",      "primary":"#5D8233","secondary":"#3A5220","accent":"#A3C460","bg":"#f5f9f0","text":"#1a2e0a"},
    {"id":"platinum",        "name":"Platinum",        "primary":"#808080","secondary":"#404040","accent":"#C0C0C0","bg":"#fafafa","text":"#1a1a1a"},
    {"id":"cobalt-flame",    "name":"Cobalt Flame",    "primary":"#003399","secondary":"#001866","accent":"#FF6600","bg":"#f0f4ff","text":"#00081a"},
    {"id":"mojave-sand",     "name":"Mojave Sand",     "primary":"#C2956A","secondary":"#8B6340","accent":"#F0C080","bg":"#fdf8f0","text":"#2e1f0a"},
    {"id":"dark-slate",      "name":"Dark Slate",      "primary":"#2F4F4F","secondary":"#1A2E2E","accent":"#66CDAA","bg":"#050e0e","text":"#d0f0e8"},
    {"id":"cherry-blossom",  "name":"Cherry Blossom",  "primary":"#FF69B4","secondary":"#C71585","accent":"#FFB6C1","bg":"#fff5f9","text":"#2e0015"},
    {"id":"obsidian",        "name":"Obsidian",        "primary":"#2D2D2D","secondary":"#111111","accent":"#888888","bg":"#050505","text":"#e8e8e8"},
    {"id":"copper-green",    "name":"Copper Green",    "primary":"#4E8B6B","secondary":"#2D5A40","accent":"#B87333","bg":"#f5faf7","text":"#0d2018"},
    {"id":"crimson-gold",    "name":"Crimson Gold",    "primary":"#8B0000","secondary":"#5A0000","accent":"#FFD700","bg":"#0d0000","text":"#fff8e0"},
]

THEME_CSS = {
    "minimal-edge":  "--font-heading:'DM Sans',sans-serif;--font-body:'DM Sans',sans-serif;--radius:2px;--shadow:0 1px 3px rgba(0,0,0,0.1);--section-padding:100px 0;",
    "bold-studio":   "--font-heading:'Syne',sans-serif;--font-body:'Inter',sans-serif;--radius:0px;--shadow:4px 4px 0px var(--primary);--section-padding:120px 0;",
    "classic-pro":   "--font-heading:'Playfair Display',serif;--font-body:'Source Sans 3',sans-serif;--radius:4px;--shadow:0 4px 20px rgba(0,0,0,0.08);--section-padding:100px 0;",
    "neon-future":   "--font-heading:'Orbitron',sans-serif;--font-body:'Rajdhani',sans-serif;--radius:0px;--shadow:0 0 20px var(--accent);--section-padding:120px 0;",
    "organic-warm":  "--font-heading:'Fraunces',serif;--font-body:'Nunito',sans-serif;--radius:16px;--shadow:0 8px 30px rgba(0,0,0,0.06);--section-padding:110px 0;",
    "magazine":      "--font-heading:'Bebas Neue',sans-serif;--font-body:'Lora',serif;--radius:0px;--shadow:none;--section-padding:80px 0;",
    "glass-dark":    "--font-heading:'Space Grotesk',sans-serif;--font-body:'Space Grotesk',sans-serif;--radius:12px;--shadow:0 8px 32px rgba(0,0,0,0.4);--section-padding:120px 0;",
    "retro-grid":    "--font-heading:'Press Start 2P',monospace;--font-body:'VT323',monospace;--radius:0px;--shadow:4px 4px 0px #000;--section-padding:100px 0;",
    "brutalist":     "--font-heading:'Anton',sans-serif;--font-body:'IBM Plex Mono',monospace;--radius:0px;--shadow:6px 6px 0px #000;--section-padding:80px 0;",
    "swiss-clean":   "--font-heading:'Helvetica Neue',sans-serif;--font-body:'Helvetica Neue',sans-serif;--radius:0px;--shadow:none;--section-padding:120px 0;",
    "luxury-gold":   "--font-heading:'Cormorant Garamond',serif;--font-body:'Cormorant',serif;--radius:2px;--shadow:0 8px 40px rgba(0,0,0,0.6);--section-padding:140px 0;",
    "pastel-soft":   "--font-heading:'Quicksand',sans-serif;--font-body:'Quicksand',sans-serif;--radius:20px;--shadow:0 4px 20px rgba(0,0,0,0.05);--section-padding:100px 0;",
    "tech-dark":     "--font-heading:'JetBrains Mono',monospace;--font-body:'JetBrains Mono',monospace;--radius:4px;--shadow:0 0 15px rgba(0,255,128,0.2);--section-padding:100px 0;",
    "earthy-sage":   "--font-heading:'Josefin Sans',sans-serif;--font-body:'Raleway',sans-serif;--radius:8px;--shadow:0 4px 15px rgba(0,0,0,0.08);--section-padding:110px 0;",
    "midnight-blue": "--font-heading:'Montserrat',sans-serif;--font-body:'Open Sans',sans-serif;--radius:6px;--shadow:0 6px 25px rgba(0,0,50,0.2);--section-padding:100px 0;",
    "coral-pop":     "--font-heading:'Paytone One',sans-serif;--font-body:'Poppins',sans-serif;--radius:12px;--shadow:0 6px 20px rgba(255,107,107,0.3);--section-padding:100px 0;",
    "monochrome":    "--font-heading:'Archivo Black',sans-serif;--font-body:'Archivo',sans-serif;--radius:0px;--shadow:2px 2px 0px #000;--section-padding:100px 0;",
    "forest-deep":   "--font-heading:'Spectral',serif;--font-body:'Karla',sans-serif;--radius:8px;--shadow:0 8px 30px rgba(0,60,0,0.15);--section-padding:110px 0;",
    "sunset-grad":   "--font-heading:'Righteous',sans-serif;--font-body:'Mulish',sans-serif;--radius:10px;--shadow:0 8px 25px rgba(200,80,0,0.2);--section-padding:120px 0;",
    "arctic-white":  "--font-heading:'Barlow',sans-serif;--font-body:'Barlow',sans-serif;--radius:4px;--shadow:0 2px 10px rgba(0,0,0,0.06);--section-padding:100px 0;",
    "cinematic":     "--font-heading:'Big Shoulders Display',sans-serif;--font-body:'Crimson Text',serif;--radius:2px;--shadow:0 10px 40px rgba(0,0,0,0.8);--section-padding:140px 0;",
    "playful-bold":  "--font-heading:'Fredoka One',sans-serif;--font-body:'Nunito',sans-serif;--radius:24px;--shadow:0 6px 20px rgba(0,0,0,0.12);--section-padding:100px 0;",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def render_ctx(s, nav, socials):
    scheme = next((c for c in COLOR_SCHEMES if c['id'] == s['color_scheme']), COLOR_SCHEMES[0])
    theme_css = THEME_CSS.get(s['theme'], THEME_CSS['bold-studio'])
    return dict(s=s, nav=nav, socials=socials, scheme=scheme, theme_css=theme_css)

def execute(conn, sql, params=()):
    """Execute with the right placeholder style."""
    if USE_POSTGRES:
        sql = sql.replace('?', '%s')
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur

# ─── SITE ROUTES ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with db() as conn:
        s = get_settings(conn)
        if s['maintenance_mode']:
            return render_template('site/maintenance.html', s=s)
        home = get_home_page(conn)
        sections   = get_sections(conn, home['id'], enabled_only=True) if home else []
        initiatives = get_initiatives(conn)
        nav    = get_nav(conn)
        socials = get_socials(conn)
    ctx = render_ctx(s, nav, socials)
    return render_template('site/index.html', sections=sections, initiatives=initiatives, **ctx)

@app.route('/page/<slug>')
def site_page(slug):
    with db() as conn:
        s = get_settings(conn)
        if s['maintenance_mode']:
            return render_template('site/maintenance.html', s=s)
        page = get_page_by_slug(conn, slug)
        if not page or not page['visible']:
            return render_template('site/404.html', s=s, nav=get_nav(conn),
                                   socials=get_socials(conn),
                                   scheme=next((c for c in COLOR_SCHEMES if c['id']==s['color_scheme']),COLOR_SCHEMES[0]),
                                   theme_css=THEME_CSS.get(s['theme'],THEME_CSS['bold-studio'])), 404
        sections = get_sections(conn, page['id'], enabled_only=True)
        nav    = get_nav(conn)
        socials = get_socials(conn)
    ctx = render_ctx(s, nav, socials)
    return render_template('site/page.html', page=page, sections=sections, **ctx)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── ADMIN AUTH ───────────────────────────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if (request.form.get('username') == ADMIN_USERNAME and
                request.form.get('password') == ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid credentials. Please try again.'
    return render_template('admin/login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ─── ADMIN DASHBOARD ─────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    with db() as conn:
        s = get_settings(conn)
        pages = get_pages(conn)
    return render_template('admin/dashboard.html', s=s, pages=pages,
                           themes=THEMES, schemes=COLOR_SCHEMES)

# ─── ADMIN SETTINGS ───────────────────────────────────────────────────────────
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    with db() as conn:
        s = get_settings(conn)
        if request.method == 'POST':
            f = request.form
            anim  = 1 if 'animations_enabled'      in f else 0
            ann   = 1 if 'announcement_bar_enabled' in f else 0
            maint = 1 if 'maintenance_mode'         in f else 0
            logo_url = s['logo_url']
            fav_url  = s['favicon_url']
            for field in ['logo', 'favicon']:
                file = request.files.get(field)
                if file and file.filename and allowed_file(file.filename):
                    fname = secure_filename(f"{field}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    if field == 'logo': logo_url = fname
                    else:               fav_url  = fname
            execute(conn, """
                UPDATE site_settings SET
                    site_name=?, tagline=?, theme=?, color_scheme=?,
                    logo_url=?, favicon_url=?, footer_text=?,
                    contact_email=?, contact_phone=?, contact_address=?, contact_hours=?,
                    meta_title=?, meta_description=?,
                    animations_enabled=?, announcement_bar_enabled=?,
                    announcement_text=?, announcement_link=?,
                    maintenance_mode=?, maintenance_message=?,
                    button_style=?, button_radius=?,
                    container_max_width=?, container_justify=?,
                    nav_style=?,
                    font_heading=?, font_body=?, font_mono=?
                WHERE id=1
            """, (
                f.get('site_name',''), f.get('tagline',''),
                f.get('theme','bold-studio'), f.get('color_scheme','crimson-black'),
                logo_url, fav_url, f.get('footer_text',''),
                f.get('contact_email',''), f.get('contact_phone',''),
                f.get('contact_address',''), f.get('contact_hours',''),
                f.get('meta_title',''), f.get('meta_description',''),
                anim, ann, f.get('announcement_text',''), f.get('announcement_link',''),
                maint, f.get('maintenance_message',''),
                f.get('button_style','solid'), int(f.get('button_radius', 6)),
                int(f.get('container_max_width', 1200)), f.get('container_justify','center'),
                f.get('nav_style','slide-right'),
                f.get('font_heading',''), f.get('font_body',''), f.get('font_mono','')
            ))
            flash('Settings saved!', 'success')
            return redirect(url_for('admin_settings'))
        return render_template('admin/settings.html', s=s, themes=THEMES, schemes=COLOR_SCHEMES)

# ─── ADMIN PAGES ─────────────────────────────────────────────────────────────
@app.route('/admin/pages')
@admin_required
def admin_pages():
    with db() as conn:
        pages = get_pages(conn)
    return render_template('admin/pages.html', pages=pages)

@app.route('/admin/pages/new', methods=['GET', 'POST'])
@admin_required
def admin_new_page():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        slug  = request.form.get('slug','').strip()
        with db() as conn:
            n = count(conn, 'pages')
            execute(conn, "INSERT INTO pages (title,slug,is_home,visible,ord) VALUES (?,?,0,1,?)", (title, slug, n))
            page_id = last_insert_id(conn, 'pages')
            execute(conn, "INSERT INTO sections (page_id,type,ord,enabled,heading,subheading,content) VALUES (?,?,0,1,?,?,'<p>Edit this content in the admin panel.</p>')",
                    (page_id, 'hero', title, 'Subtitle goes here'))
            execute(conn, "INSERT INTO sections (page_id,type,ord,enabled,heading,content) VALUES (?,?,1,1,'Content','<p>Add your content here.</p>')",
                    (page_id, 'content'))
        flash('Page created!', 'success')
        return redirect(url_for('admin_edit_page', page_id=page_id))
    return render_template('admin/new_page.html')

@app.route('/admin/pages/<int:page_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_page(page_id):
    with db() as conn:
        page = get_page_by_id(conn, page_id)
        if not page:
            flash('Page not found.', 'error')
            return redirect(url_for('admin_pages'))
        if request.method == 'POST' and request.form.get('action') == 'update_page':
            visible   = 1 if 'visible' in request.form else 0
            new_slug  = page['slug'] if page['is_home'] else request.form.get('slug', page['slug'])
            execute(conn, "UPDATE pages SET title=?,slug=?,visible=? WHERE id=?",
                    (request.form.get('title', page['title']), new_slug, visible, page_id))
            flash('Page updated!', 'success')
            page = get_page_by_id(conn, page_id)
        sections = get_sections(conn, page_id)
    return render_template('admin/edit_page.html', page=page, sections=sections)

@app.route('/admin/pages/<int:page_id>/delete', methods=['POST'])
@admin_required
def admin_delete_page(page_id):
    with db() as conn:
        page = get_page_by_id(conn, page_id)
        if page and page['is_home']:
            flash("Cannot delete the home page.", 'error')
            return redirect(url_for('admin_pages'))
        execute(conn, "DELETE FROM sections WHERE page_id=?", (page_id,))
        execute(conn, "DELETE FROM pages WHERE id=?", (page_id,))
    flash('Page deleted.', 'success')
    return redirect(url_for('admin_pages'))

# ─── ADMIN SECTIONS ───────────────────────────────────────────────────────────
@app.route('/admin/sections/<int:section_id>', methods=['POST'])
@admin_required
def admin_update_section(section_id):
    with db() as conn:
        cur = execute(conn, "SELECT * FROM sections WHERE id=?", (section_id,))
        sec = cur.fetchone()
        if not sec:
            flash('Section not found.', 'error')
            return redirect(url_for('admin_pages'))
        sec = dict(sec)
        f = request.form
        enabled   = 1 if 'enabled' in f else 0
        btn_new_tab = 1 if 'button_new_tab' in f else 0
        image_url = sec['image_url']
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            fname = secure_filename(f"sec_{section_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            image_url = fname
        execute(conn, """
            UPDATE sections SET heading=?,subheading=?,content=?,
            button_text=?,button_link=?,button_new_tab=?,enabled=?,image_url=?,image_alt=?,
            image_position=?,image_size=?,image_overlay=?,image_overlay_color=?,image_blur=?,
            icon_style=?,icon_border=?,icon_hover=?
            WHERE id=?
        """, (f.get('heading',''), f.get('subheading',''), f.get('content',''),
              f.get('button_text',''), f.get('button_link',''), btn_new_tab, enabled,
              image_url, f.get('image_alt',''),
              f.get('image_position','center'), f.get('image_size','cover'),
              _safe_float(f.get('image_overlay', 0)), f.get('image_overlay_color','#000000'),
              _safe_int(f.get('image_blur', 0)),
              f.get('icon_style','default'), f.get('icon_border','none'), f.get('icon_hover','zoom'),
              section_id))
        page_id = sec['page_id']
    flash('Section saved!', 'success')
    return redirect(url_for('admin_edit_page', page_id=page_id))

@app.route('/admin/sections/add/<int:page_id>', methods=['POST'])
@admin_required
def admin_add_section(page_id):
    sec_type = request.form.get('type', 'content')
    with db() as conn:
        n = count(conn, 'sections')
        execute(conn, "INSERT INTO sections (page_id,type,ord,enabled,heading,subheading,content) VALUES (?,?,?,1,'New Section','','<p>Edit this content.</p>')",
                (page_id, sec_type, n))
    flash('Section added!', 'success')
    return redirect(url_for('admin_edit_page', page_id=page_id))

@app.route('/admin/sections/<int:section_id>/delete', methods=['POST'])
@admin_required
def admin_delete_section(section_id):
    with db() as conn:
        cur = execute(conn, "SELECT page_id FROM sections WHERE id=?", (section_id,))
        row = cur.fetchone()
        page_id = dict(row)['page_id'] if row else None
        execute(conn, "DELETE FROM sections WHERE id=?", (section_id,))
    flash('Section deleted.', 'success')
    return redirect(url_for('admin_edit_page', page_id=page_id))

# ─── ADMIN NAV ────────────────────────────────────────────────────────────────
@app.route('/admin/nav', methods=['GET', 'POST'])
@admin_required
def admin_nav():
    with db() as conn:
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                n = count(conn, 'nav_items')
                execute(conn, "INSERT INTO nav_items (label,url,icon,ord) VALUES (?,?,?,?)",
                        (request.form.get('label'), request.form.get('url'),
                         request.form.get('icon',''), n))
                flash('Nav link added!', 'success')
            elif action == 'delete':
                execute(conn, "DELETE FROM nav_items WHERE id=?", (request.form.get('id'),))
                flash('Nav link removed.', 'success')
        nav = get_nav(conn)
    return render_template('admin/nav.html', nav=nav)

# ─── ADMIN SOCIALS ────────────────────────────────────────────────────────────
@app.route('/admin/socials', methods=['GET', 'POST'])
@admin_required
def admin_socials():
    with db() as conn:
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                execute(conn, "INSERT INTO social_links (platform,url,icon) VALUES (?,?,?)",
                        (request.form.get('platform'), request.form.get('url'),
                         request.form.get('icon','fa-solid fa-link')))
                flash('Social link added!', 'success')
            elif action == 'delete':
                execute(conn, "DELETE FROM social_links WHERE id=?", (request.form.get('id'),))
                flash('Social link removed.', 'success')
        socials = get_socials(conn)
    return render_template('admin/socials.html', socials=socials)

# ─── ADMIN INITIATIVES ────────────────────────────────────────────────────────
@app.route('/admin/initiatives', methods=['GET', 'POST'])
@admin_required
def admin_initiatives():
    with db() as conn:
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                n = count(conn, 'initiatives')
                execute(conn, "INSERT INTO initiatives (title,description,button_text,button_link,icon,ord) VALUES (?,?,?,?,?,?)",
                        (request.form.get('title','New Initiative'),
                         request.form.get('description',''),
                         request.form.get('button_text','Learn More'),
                         request.form.get('button_link','#'),
                         request.form.get('icon','fa-solid fa-star'), n))
                flash('Initiative added!', 'success')
            elif action == 'delete':
                execute(conn, "DELETE FROM initiatives WHERE id=?", (request.form.get('id'),))
                flash('Initiative deleted.', 'success')
        initiatives = get_all_initiatives(conn)
    return render_template('admin/initiatives.html', initiatives=initiatives)

@app.route('/admin/initiatives/<int:init_id>', methods=['POST'])
@admin_required
def admin_update_initiative(init_id):
    f = request.form
    btn_new_tab = 1 if 'button_new_tab' in f else 0
    with db() as conn:
        execute(conn, "UPDATE initiatives SET title=?,description=?,button_text=?,button_link=?,button_new_tab=?,icon=? WHERE id=?",
                (f.get('title'), f.get('description'), f.get('button_text'),
                 f.get('button_link'), btn_new_tab, f.get('icon'), init_id))
    flash('Initiative updated!', 'success')
    return redirect(url_for('admin_initiatives'))

# ─── SEED ─────────────────────────────────────────────────────────────────────
def seed():
    with db() as conn:
        if count(conn, 'site_settings') == 0:
            execute(conn, "INSERT INTO site_settings (id) VALUES (1)")
        if count(conn, 'pages') == 0:
            execute(conn, "INSERT INTO pages (title,slug,is_home,visible,ord) VALUES ('Home','home',1,1,0)")
            cur = execute(conn, "SELECT id FROM pages WHERE is_home=1")
            home_id = dict(cur.fetchone())['id']
            for i,(typ,h,sub,cont,bt,bl,img) in enumerate([
                ('hero','Clinton Tech Dev Suite','Building Digital Experiences That Matter',
                 'Professional web development solutions tailored for your business.','View My Work','#portfolio','default-hero.svg'),
                ('services','What I Build','Full-stack solutions from concept to launch','','','','default-services.svg'),
                ('about','About Me','Developer & Digital Craftsman',
                 '<p>I specialise in creating high-performance websites and web applications that help businesses grow online.</p>','Download CV','#','default-about.svg'),
                ('portfolio','Portfolio','Recent Work','','','','default-portfolio.svg'),
                ('contact','Get In Touch',"Let's build something great together",'','','','default-contact.svg'),
            ]):
                execute(conn, "INSERT INTO sections (page_id,type,ord,enabled,heading,subheading,content,button_text,button_link,image_url) VALUES (?,?,?,1,?,?,?,?,?,?)",
                        (home_id,typ,i,h,sub,cont,bt,bl,img))
            for i,(lbl,url,icon) in enumerate([
                ('Home','/','fa-solid fa-house'),
                ('Portfolio','/#portfolio','fa-solid fa-briefcase'),
                ('Services','/#services','fa-solid fa-code'),
                ('Contact','/#contact','fa-solid fa-envelope'),
            ]):
                execute(conn, "INSERT INTO nav_items (label,url,icon,ord) VALUES (?,?,?,?)",(lbl,url,icon,i))
            for plat,url,icon in [
                ('GitHub','https://github.com','fa-brands fa-github'),
                ('LinkedIn','https://linkedin.com','fa-brands fa-linkedin'),
                ('Twitter/X','https://twitter.com','fa-brands fa-x-twitter'),
            ]:
                execute(conn, "INSERT INTO social_links (platform,url,icon) VALUES (?,?,?)",(plat,url,icon))
            for i,(title,desc,icon) in enumerate([
                ('Static Websites','Lightning-fast static sites with perfect Lighthouse scores, deployed globally.','fa-solid fa-bolt'),
                ('Web Applications','Full-stack apps with robust backends, databases, auth, and APIs.','fa-solid fa-layer-group'),
                ('E-Commerce','Online stores optimised for conversions and seamless user experience.','fa-solid fa-cart-shopping'),
            ]):
                execute(conn, "INSERT INTO initiatives (title,description,button_text,button_link,icon,ord) VALUES (?,?,'Learn More','#contact',?,?)",
                        (title,desc,icon,i))

# ─── STARTUP ─────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()
    seed()

if __name__ == '__main__':
    app.run(debug=True)

# ─── GALLERY (import extra db helpers) ───────────────────────────────────────
from database import init_gallery, get_gallery_items, get_gallery_categories, get_all_gallery_items

GALLERY_ALLOWED = {'png','jpg','jpeg','webp','gif','mp4','mov','webm','ogg'}

def gallery_allowed(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in GALLERY_ALLOWED

def is_video(filename):
    return filename.rsplit('.',1)[-1].lower() in {'mp4','mov','webm','ogg'}

# Site-facing gallery page
@app.route('/gallery')
def gallery_page():
    cat = request.args.get('cat', 'All')
    with db() as conn:
        s = get_settings(conn)
        if s['maintenance_mode']:
            return render_template('site/maintenance.html', s=s)
        init_gallery(conn)
        items = get_gallery_items(conn, category=cat if cat != 'All' else None)
        categories = ['All'] + get_gallery_categories(conn)
        nav = get_nav(conn)
        socials = get_socials(conn)
    ctx = render_ctx(s, nav, socials)
    return render_template('site/gallery.html', items=items, categories=categories,
                           active_cat=cat, is_video=is_video, **ctx)

# Admin gallery
@app.route('/admin/gallery')
@admin_required
def admin_gallery():
    with db() as conn:
        init_gallery(conn)
        items = get_all_gallery_items(conn)
    return render_template('admin/gallery.html', items=items, is_video=is_video)

@app.route('/admin/gallery/upload', methods=['POST'])
@admin_required
def admin_gallery_upload():
    files = request.files.getlist('media')
    title    = request.form.get('title','')
    caption  = request.form.get('caption','')
    category = request.form.get('category','General').strip() or 'General'
    with db() as conn:
        init_gallery(conn)
        n = count(conn, 'gallery_items')
        for file in files:
            if file and file.filename and gallery_allowed(file.filename):
                ext  = file.filename.rsplit('.',1)[1].lower()
                fname = secure_filename(f"gallery_{n}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                mtype = 'video' if is_video(fname) else 'image'
                execute(conn, "INSERT INTO gallery_items (title,caption,media_type,filename,category,ord) VALUES (?,?,?,?,?,?)",
                        (title or file.filename, caption, mtype, fname, category, n))
                n += 1
    flash('Media uploaded!', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/admin/gallery/<int:item_id>/delete', methods=['POST'])
@admin_required
def admin_gallery_delete(item_id):
    with db() as conn:
        init_gallery(conn)
        cur = execute(conn, "SELECT filename FROM gallery_items WHERE id=?", (item_id,))
        row = cur.fetchone()
        if row:
            fname = dict(row)['filename']
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            if os.path.exists(fpath):
                os.remove(fpath)
        execute(conn, "DELETE FROM gallery_items WHERE id=?", (item_id,))
    flash('Item deleted.', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/admin/gallery/<int:item_id>/toggle', methods=['POST'])
@admin_required
def admin_gallery_toggle(item_id):
    with db() as conn:
        init_gallery(conn)
        cur = execute(conn, "SELECT enabled FROM gallery_items WHERE id=?", (item_id,))
        row = cur.fetchone()
        if row:
            current = dict(row)['enabled']
            execute(conn, "UPDATE gallery_items SET enabled=? WHERE id=?", (0 if current else 1, item_id))
    return redirect(url_for('admin_gallery'))

@app.route('/admin/gallery/<int:item_id>/edit', methods=['POST'])
@admin_required
def admin_gallery_edit(item_id):
    f = request.form
    with db() as conn:
        init_gallery(conn)
        execute(conn, "UPDATE gallery_items SET title=?,caption=?,category=? WHERE id=?",
                (f.get('title',''), f.get('caption',''), f.get('category','General'), item_id))
    flash('Item updated.', 'success')
    return redirect(url_for('admin_gallery'))

# ─── STATIC EXPORT ────────────────────────────────────────────────────────────
import tempfile, threading
from exporter import export_static, zip_export
from flask import send_file

_export_lock = threading.Lock()
_export_status = {'running': False, 'done': False, 'summary': None, 'error': None}

@app.route('/admin/export')
@admin_required
def admin_export():
    with db() as conn:
        s = get_settings(conn)
        pages = get_pages(conn)
    return render_template('admin/export.html', s=s, pages=pages,
                           status=_export_status)

@app.route('/admin/export/run', methods=['POST'])
@admin_required
def admin_export_run():
    global _export_status
    if _export_status['running']:
        flash('Export already in progress.', 'error')
        return redirect(url_for('admin_export'))

    _export_status = {'running': True, 'done': False, 'summary': None, 'error': None}

    def do_export():
        global _export_status
        try:
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'export_out')
            summary = export_static(app, out_dir)
            _export_status['summary'] = summary
            _export_status['done']    = True
        except Exception as e:
            _export_status['error'] = str(e)
        finally:
            _export_status['running'] = False

    t = threading.Thread(target=do_export, daemon=True)
    t.start()
    t.join(timeout=120)   # wait up to 2 min synchronously

    return redirect(url_for('admin_export'))

@app.route('/admin/export/download')
@admin_required
def admin_export_download():
    out_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'export_out')
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'site_export.zip')

    if not os.path.isdir(out_dir):
        flash('No export found. Run export first.', 'error')
        return redirect(url_for('admin_export'))

    with db() as conn:
        s = get_settings(conn)
    site_name = s['site_name'].lower().replace(' ', '-')
    from datetime import datetime
    fname = f"{site_name}-static-{datetime.now().strftime('%Y%m%d')}.zip"

    zip_export(out_dir, zip_path)
    return send_file(zip_path, as_attachment=True, download_name=fname,
                     mimetype='application/zip')
