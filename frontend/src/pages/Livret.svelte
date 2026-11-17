<script>
  // Un livret : relecture bloc par bloc à gauche, aperçu des 4 pages à droite. « Approuver » contrôle
  // d'abord qu'aucune page ne déborde. Rien ne s'imprime sans approbation.
  // Une page qui déborde : ses blocs passent en rouge, avec un compteur qui suit la frappe (lib/place.js),
  // et les propositions de remplacement qui la feraient tenir sont en vert.
  import { onMount, onDestroy, setContext } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Cake from '@lucide/svelte/icons/cake'
  import Download from '@lucide/svelte/icons/download'
  import EyeOff from '@lucide/svelte/icons/eye-off'
  import Eye from '@lucide/svelte/icons/eye'
  import Replace from '@lucide/svelte/icons/replace'
  import Plus from '@lucide/svelte/icons/plus'
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Etat from '$lib/Etat.svelte'
  import FicheForm from '$lib/FicheForm.svelte'
  import Propositions from '$lib/Propositions.svelte'
  import IaBloc from '$lib/IaBloc.svelte'
  import Element from '$lib/Element.svelte'
  import Relecture from '$lib/Relecture.svelte'
  import { enfiler } from '$lib/fileIa.svelte.js'
  import { dateCourte, dateLongue, PORTEES } from '$lib/format.js'
  import { etatPlace } from '$lib/place.js'

  let { id, onchange, ondeconnecte } = $props()
  let d = $state(null)
  let contenu = $state(null)
  let mot = $state('')
  // 0.13 : photo d'Immich en page 4 (une des 6 proposées) et message du code-barres
  let photo = $state({})
  let codeBarres = $state('')
  let propsLegende = $state([])
  let ctxPhoto = $state(null)
  let demande = $state('')
  // 0.14 : bouton « IA » du haut — toutes les aides de tous les blocs, une après l'autre
  const ias = {}                   // composants IaBloc par bloc (bind:this)
  // 0.17 : relecture élément par élément (Valider, IA, Changer, Refuser), commune avec La Récidive
  let valides = $state({})         // {clé d'élément : empreinte validée}, enregistré avec le livret
  let revoir = $state(false)
  const registre = $state({})      // {clé : validé ?}, tenu par chaque Element
  setContext('validation', {
    valides: () => valides, revoir: () => revoir, registre,
    trop: (n) => !!(place.pages[n] && !place.pages[n].ok),
    valider: async (cle, h) => { valides = { ...valides, [cle]: h }; await enregistrer(true) },
  })
  const total = $derived(Object.keys(registre).length)
  const restants = $derived(Object.values(registre).filter((x) => !x).length)
  const fini = $derived(total > 0 && restants === 0)
  // Une partie reste affichée tant qu'elle a un élément à valider (ou aucun élément : de quoi en ajouter)
  function aFaire(...prefixes) {
    if (revoir) return true
    const miens = Object.entries(registre).filter(([k]) => prefixes.some((p) => k === p || k.startsWith(p + ':')))
    return !miens.length || miens.some(([, ok]) => !ok)
  }
  let lot = $state(null)           // {fait, total} pendant le tour complet
  let modifie = $state(false)
  let message = $state('')
  let attente = $state('')
  let ouvert = $state(null)        // {bloc, index} du sélecteur de propositions
  let ficheOuverte = $state(false)
  let avant = $state({ sejours_avant: 0, dernier_avant: '' })   // 0.9 : séjours d'avant Gazette (N° de La Récidive)
  let tampon = $state(Date.now())
  let largeur = $state(400)
  let mes = $state(null)           // mesure de Chromium du livret enregistré (null : pas de mesure)
  let minuteur = null

  async function lire() {
    try {
      d = await api.get(`/api/livrets/${id}`)
      contenu = JSON.parse(JSON.stringify(d.livret.contenu))
      mot = d.livret.mot || d.livret.mot_defaut
      photo = { ...(d.livret.photo ?? {}) }
      propsLegende = d.livret.photo?.propositions ?? []
      ctxPhoto = d.livret.photo?.contexte ?? null
      codeBarres = d.livret.code_barres || ''
      valides = { ...(d.livret.valides ?? {}) }
      avant = { sejours_avant: d.personne.sejours_avant ?? 0, dernier_avant: d.personne.dernier_avant ?? '' }
      modifie = false
      tampon = Date.now()
      clearTimeout(minuteur)
      if (d.livret.etat === 'en_preparation') minuteur = setTimeout(lire, 3000)
      else mesurer()
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  function toucher() { modifie = true; message = '' }
  const corps = () => ({ contenu: $state.snapshot(contenu), mot, code_barres: codeBarres, valides: $state.snapshot(valides),
                         photo: photo.id ? { id: photo.id, cadrage: photo.cadrage ?? 'haut', legende: photo.legende ?? '', description: photo.description ?? '' } : null })
  const ctxTexte = (c) => !c ? '' : [c.albums?.length ? `Album : ${c.albums.join(', ')}` : '', c.personnes?.length ? `Avec : ${c.personnes.join(', ')}` : '']
    .filter(Boolean).join(' · ')
  function prendrePhoto(x) {
    if (photo.id === x.id) { photo = {}; propsLegende = []; ctxPhoto = null }
    else { photo = { id: x.id, date: x.date, cadrage: 'haut', legende: '', description: '' }; propsLegende = []; ctxPhoto = null }
    toucher()
  }
  async function chercherPhotos() {
    demande = 'photos'
    try { const r = await api.post(`/api/livrets/${id}/photos`, {}); d.livret.photos_choix = r.photos_choix; message = r.message }
    catch (err) { message = err.message }
    demande = ''
  }
  async function proposerTout() {
    const liste = Object.entries(ias).filter(([, c]) => c)
    lot = { fait: 0, total: liste.length + (photo.id ? 1 : 0) }
    message = ''
    let faites = 0, echec = ''
    for (const [, c] of liste) {
      const r = await c.tout()
      faites += r.faites
      if (r.erreur) { echec = r.erreur; if (/injoignable|pas réglée|refusé/.test(r.erreur)) break }
      lot = { ...lot, fait: lot.fait + 1 }
    }
    if (photo.id && !/injoignable|pas réglée|refusé/.test(echec)) {
      await enfiler('Légende de la photo', () => proposerLegende(true))
      lot = { ...lot, fait: lot.fait + 1 }
    }
    lot = null
    message = echec && !faites ? echec
      : `Propositions prêtes${echec ? ' (une partie seulement : ' + echec + ')' : ''} : touche celles qui te plaisent sous chaque bloc, puis Enregistrer.`
  }
  function photoSuivante() {
    const l = d.livret.photos_choix
    if (!l.length) return
    const i = l.findIndex((x) => x.id === photo.id)
    const x = l[(i + 1) % l.length]
    photo = { id: x.id, date: x.date, cadrage: 'haut', legende: '', description: '' }; propsLegende = []; ctxPhoto = null; toucher()
  }
  const legendeEnFile = () => enfiler('Légende de la photo', () => proposerLegende())
  async function proposerLegende(silencieux = false) {
    demande = 'legende'
    message = ''
    try {
      await api.put(`/api/livrets/${id}`, corps())           // la photo choisie doit être enregistrée avant
      const r = await api.post(`/api/livrets/${id}/photo/proposer`, { description: photo.description ?? '' })
      propsLegende = r.propositions
      ctxPhoto = r.contexte
    } catch (err) { if (!silencieux) message = err.message }
    demande = ''
  }
  async function mesurer() {
    if (!contenu?.une) { mes = null; return }
    const instantane = { contenu: $state.snapshot(contenu), mot }
    try { mes = { ...instantane, pages: (await api.get(`/api/livrets/${id}/mesure`)).pages } }
    catch { mes = null }             // sans Chromium : pas de contrôle de place, l'éditeur marche quand même
  }

  async function enregistrer(silencieux = false) {
    attente = 'enregistrer'
    try {
      await api.put(`/api/livrets/${id}`, corps())
      await lire()
      if (silencieux !== true) message = 'Enregistré.'
      onchange?.()
    } catch (err) { message = err.message }
    attente = ''
  }
  async function choisir(bloc, f, index) {
    if (modifie) await api.put(`/api/livrets/${id}`, corps())
    await api.post(`/api/livrets/${id}/choisir`, { bloc, proposition: f.id, index })
    ouvert = null
    await lire()
  }
  async function approuver() {
    if (modifie) await enregistrer()
    attente = 'approuver'
    try { await api.post(`/api/livrets/${id}/approuver`); await lire(); message = 'Livret approuvé.'; onchange?.() }
    catch (err) { message = err.message; mesurer() }
    attente = ''
  }
  async function preparer(relire = false) {
    if (relire && !confirm('Relire les sources oublie les pages gardées pour cette date et refait le livret (le mot des hôtes est gardé). Continuer ?')) return
    if (!relire && !confirm('Refaire le livret depuis les sources ? Les choix de blocs sont remplacés ; le mot des hôtes, la musique et le cinéma sont gardés.')) return
    await api.post(`/api/livrets/${id}/preparer`, { relire })
    await lire()
  }
  async function ajouterPhrase(a, phrase) {
    if (modifie) await enregistrer()
    await api.post(`/api/livrets/${id}/mot/ajouter`, { phrase, cle: a.cle })
    await lire()
    onchange?.()
  }
  async function remplirCulture() {
    if (modifie) await enregistrer()
    try { await api.post(`/api/livrets/${id}/culture`); await lire(); message = 'Musique et cinéma remplis depuis le top 5.' }
    catch (err) { message = err.message }
  }
  async function modifierFiche(fiche) {
    await api.put(`/api/personnes/${id}`, fiche)
    ficheOuverte = false
    await lire()
  }
  async function enregistrerAvant() {
    try {
      await api.put(`/api/personnes/${id}`, { sejours_avant: +avant.sejours_avant || 0, dernier_avant: avant.dernier_avant || '' })
      message = 'Séjours d\'avant Gazette enregistrés : le numéro de La Récidive des séjours à venir est recalculé.'
      await lire()
      onchange?.()
    } catch (err) { message = err.message }
  }
  async function supprimer() {
    if (!confirm(`Supprimer la fiche et le livret de ${d.personne.nom} ?`)) return
    await api.del(`/api/personnes/${id}`)
    location.hash = '#/livrets'
  }
  function basculer(o) { o.masque = !o.masque; toucher() }
  function ouvrir(bloc, index = null) { ouvert = ouvert?.bloc === bloc && ouvert?.index === index ? null : { bloc, index } }
  const evts = $derived(d?.livret.propositions.evenements ?? [])
  const annee = $derived(d?.livret.propositions.annee ?? [])
  const pris = $derived(contenu ? [contenu.une?.id, ...(contenu.breves ?? []).map((b) => b.id), ...(contenu.p2?.items ?? []).map((b) => b.id),
                                   ...(contenu.chrono ?? []).map((b) => b.id)].filter(Boolean) : [])
  const echelle = $derived(Math.min(1, largeur / 600))
  const place = $derived(etatPlace(mes, contenu, mot))
  // 0.15.2 : encadré rouge sur les réglages d'une page qui déborde à l'impression (tant qu'elle n'est pas censée tenir)
  const cadrePage = (n) => (place.pages[n] && !place.pages[n].ok ? 'border-destructive ring-2 ring-destructive/50' : '')
  const LIGNE = 17                   // hauteur d'une ligne d'article à la plus petite taille (px)
  function cadre(cle) {
    const x = place.blocs[cle]
    return !x ? '' : x.rouge ? 'rounded-lg ring-2 ring-destructive/70 p-1.5' : 'rounded-lg ring-2 ring-valide/60 p-1.5'
  }
  function bord(cle) {
    const x = place.blocs[cle]
    return !x ? '' : x.rouge ? '!border-destructive' : '!border-valide'
  }
  const tient = (cle) => (f) => place.tient(cle, f)
  // 0.12 : « Raccourcir » vise ce qui fait tenir la page (bloc en rouge), sinon les trois quarts du texte
  const cible = (cle, t) => { const x = place.blocs[cle]; return x?.rouge && x.aRetirer ? Math.max(60, x.compte - x.aRetirer) : Math.round((t || '').length * 0.75) }

  onMount(lire)
  onDestroy(() => clearTimeout(minuteur))
</script>

{#snippet bouton(bloc, index, libelle = 'Remplacer')}
  <button type="button" class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          onclick={() => ouvrir(bloc, index)} aria-expanded={ouvert?.bloc === bloc && ouvert?.index === index}>
    <Replace class="size-3.5" aria-hidden="true" />{libelle}
  </button>
{/snippet}
{#snippet compteur(cle)}
  {@const x = place.blocs[cle]}
  {#if x}
    <p class="text-xs {x.rouge ? 'text-destructive' : 'text-valide'}" aria-live="polite">
      {x.compte} signes ·
      {#if x.rouge}
        {x.seul ? `en retirer environ ${x.aRetirer} suffirait` : 'même raccourci, il ne suffit pas seul : masque-le, remplace-le ou raccourcis aussi un autre bloc'}
      {:else}
        la page devrait tenir, enregistre pour vérifier
      {/if}
    </p>
  {/if}
{/snippet}
{#snippet masquer(o)}
  <button type="button" class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" onclick={() => basculer(o)}>
    {#if o.masque}<Eye class="size-3.5" aria-hidden="true" />Montrer{:else}<EyeOff class="size-3.5" aria-hidden="true" />Masquer{/if}
  </button>
{/snippet}

<a href="#/livrets" class="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
  <ArrowLeft class="size-4" aria-hidden="true" /> Livrets
</a>

{#if d && contenu}
  <header class="sticky top-0 z-10 -mx-2 mb-5 flex flex-wrap items-end justify-between gap-3 bg-background/90 px-2 py-2 backdrop-blur">
    <div>
      <p class="etiquette">né·e le {dateLongue(d.personne.naissance)}</p>
      <h1 class="titre">{d.personne.nom}</h1>
      <p class="mt-2 flex flex-wrap items-center gap-2">
        <Etat etat={d.livret.etat} />
        {#each d.sejours as s}<span class="text-xs text-muted-foreground">chambre {s.chambre}, {dateCourte(s.du)} → {dateCourte(s.jusqu_au)}</span>{/each}
      </p>
    </div>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" onclick={proposerTout} disabled={!!attente || lot !== null || demande !== '' || d.livret.etat === 'en_preparation'}
              title="L'IA du PC relit tous les textes et fait ses propositions sous chaque bloc">
        <Sparkles class="size-4" aria-hidden="true" />{lot ? `IA ${lot.fait}/${lot.total}` : 'IA'}</Button>
      {#if modifie}<Button variant="outline" onclick={enregistrer} disabled={!!attente}>Enregistrer</Button>{/if}
      <Button onclick={approuver} disabled={!!attente || d.livret.etat === 'en_preparation' || d.livret.etat === 'approuve' && !modifie}>
        {attente === 'approuver' ? 'Contrôle…' : d.livret.etat === 'approuve' && !modifie ? 'Approuvé' : 'Approuver'}
      </Button>
    </div>
  </header>

  {#if d.personne.essai_de}
    <p class="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/60 px-4 py-2 text-sm" role="status">
      <span>Gazette d'essai (simulation) : elle ne compte pas et ne touche pas au vrai livret.</span>
      <button type="button" class="text-xs underline hover:text-destructive" onclick={async () => { await api.del(`/api/essais/gazette/${id}`); location.hash = '#/reglages' }}>Supprimer l'essai</button>
    </p>
  {/if}
  {#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}
  {#each Object.entries(place.pages) as [n, p]}
    <p class="mb-3 rounded-xl border px-4 py-2 text-sm {p.ok ? 'border-valide/60 text-valide' : 'border-destructive/60 text-destructive'}" role="status">
      {#if p.ok}Page {n} : elle devrait tenir maintenant. Enregistre pour vérifier.
      {:else}Page {n} trop pleine : il manque environ {Math.max(1, Math.ceil(p.reste / LIGNE))} ligne{Math.ceil(p.reste / LIGNE) > 1 ? 's' : ''}. Blocs en rouge : raccourcis-en un, masque-le ou remplace-le par une proposition en vert.{/if}
    </p>
  {/each}
  {#if d.livret.erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm text-destructive" role="alert">{d.livret.erreur}</p>{/if}

  {#each d.anniversaires.filter((a) => !a.ignore) as a}
    <section class="mb-4 rounded-2xl border border-primary/60 bg-card p-4" aria-label="Anniversaire">
      <p class="flex items-center gap-2 font-medium"><Cake class="size-5 text-primary" aria-hidden="true" />
        Anniversaire {a.libelle} : le {dateLongue(a.anniversaire)} (séjour du {dateCourte(a.sejour.du)} au {dateCourte(a.sejour.jusqu_au)})</p>
      <ul class="mt-2 grid gap-2">
        {#each a.phrases as p}
          <li class="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span class="font-serif italic">« {p} »</span>
            <Button size="sm" variant="outline" onclick={() => ajouterPhrase(a, p)}>Ajouter au mot des hôtes</Button>
          </li>
        {/each}
      </ul>
    </section>
  {/each}

  {#if d.livret.etat === 'en_preparation'}
    <p class="mb-4 text-sm text-muted-foreground" role="status">Lecture des sources… (Wikipédia demande des pauses entre deux pages : une à deux minutes.)</p>
  {/if}

  <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
    <div class="grid min-w-0 content-start gap-4">
      <Relecture {restants} {total} bind:revoir {approuver} {attente} etat={d.livret.etat} {modifie} journal="la Gazette" />
      <div class="grid min-w-0 content-start gap-4" class:hidden={fini && !revoir}>
      <!-- La une -->
      <section class="min-w-0 rounded-2xl border bg-card p-4 {cadrePage(1)}" class:hidden={!aFaire('une')} aria-label="La une">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 1 · la une ({PORTEES[contenu.une?.portee] ?? '—'})</h2></div>
        <Element cle="une" page={1} titre="La une" valeur={{ t: contenu.une.titre, c: contenu.une.chapo, e: contenu.une.encart }}
                 onia={() => ias.une?.tout()} onchanger={() => ouvrir('une')} changer="Un autre événement">
        <input class="mb-2 w-full rounded-lg border bg-background px-3 py-2 font-serif text-lg font-semibold {bord('une')}" bind:value={contenu.une.titre} oninput={toucher} aria-label="Gros titre" />
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 text-sm {bord('une')}" rows="3" bind:value={contenu.une.chapo} oninput={toucher} aria-label="Chapeau"></textarea>
        {@render compteur('une')}
        <IaBloc bind:this={ias.une} nom="La une" pid={id} texte={() => contenu.une.chapo} actions={['titres', 'raccourcir', 'journal', 'traduire']} signes={cible('une', contenu.une.chapo)}
                onapply={(a, t) => { if (a === 'titres') contenu.une.titre = t; else contenu.une.chapo = t; toucher() }} />
        <div class="mt-2 grid grid-cols-3 gap-2 text-sm">
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.une.encart.k} oninput={toucher} aria-label="Encart : rubrique" />
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1 font-semibold" bind:value={contenu.une.encart.v} oninput={toucher} aria-label="Encart : nombre" />
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1" bind:value={contenu.une.encart.l} oninput={toucher} aria-label="Encart : légende" />
        </div>
        {#if ouvert?.bloc === 'une'}<Propositions liste={evts} choisis={pris} tient={tient('une')} onchoisir={(f) => choisir('une', f)} onfermer={() => (ouvert = null)} />{/if}
        </Element>
      </section>

      <!-- Brèves -->
      <section class="min-w-0 rounded-2xl border bg-card p-4 {cadrePage(1)}" class:hidden={!aFaire('breve')} aria-label="Brèves">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 1 · brèves</h2>{@render bouton('breve', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'breve' && ouvert.index === null}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('breve', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-3">
          {#each contenu.breves as b, i}
            <li class="{b.masque ? 'opacity-45' : ''}">
              <Element cle="breve:{b.id ?? i}" page={1} titre="Brève {i + 1}" valeur={{ t: b.titre, x: b.texte, m: !!b.masque }}
                       onia={() => ias[`breve:${i}`]?.tout()} onchanger={() => ouvrir('breve', i)} changer="Un autre événement"
                       onrefuser={() => { contenu.breves.splice(i, 1); toucher() }}>
              <div class="grid gap-1 {cadre(`breve:${i}`)}">
                <input class="min-w-0 rounded-lg border bg-background px-2 py-1 text-sm font-semibold" bind:value={b.titre} oninput={toucher} aria-label="Titre de la brève {i + 1}" />
              <textarea class="rounded-lg border bg-background px-2 py-1 text-sm [field-sizing:content] min-h-14" rows="2" bind:value={b.texte} oninput={toucher} aria-label="Texte de la brève {i + 1}"></textarea>
              {@render compteur(`breve:${i}`)}
              <IaBloc bind:this={ias[`breve:${i}`]} nom="Brève {i + 1}" pid={id} texte={() => b.texte} actions={['titres', 'raccourcir', 'journal', 'traduire']} signes={cible(`breve:${i}`, b.texte)}
                      onapply={(a, t) => { if (a === 'titres') b.titre = t; else b.texte = t; toucher() }} />
              {#if ouvert?.bloc === 'breve' && ouvert.index === i}<Propositions liste={evts} choisis={pris} tient={tient(`breve:${i}`)} onchoisir={(f) => choisir('breve', f, i)} onfermer={() => (ouvert = null)} />{/if}
              </div>
              </Element>
            </li>
          {/each}
        </ul>
      </section>

      <!-- Page 2 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4 {cadrePage(2)}" class:hidden={!aFaire('p2')} aria-label="Page 2">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 2 · {contenu.p2.mode === 'mois' ? 'les titres du mois' : 'la semaine'}</h2>{@render bouton('p2', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'p2' && ouvert.index === null}<Propositions liste={evts} choisis={pris} onchoisir={(f) => choisir('p2', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-3">
          {#each contenu.p2.items as it, i}
            <li class="{it.masque ? 'opacity-45' : ''}">
              <Element cle="p2:{it.id ?? i}" page={2} titre="Page 2 · {dateCourte(it.date)}" valeur={{ t: it.titre, x: it.texte, m: !!it.masque }}
                       onia={() => ias[`p2:${i}`]?.tout()} onchanger={() => ouvrir('p2', i)} changer="Un autre événement"
                       onrefuser={() => { contenu.p2.items.splice(i, 1); toucher() }}>
              <div class="grid gap-1 {cadre(`p2:${i}`)}">
                <input class="min-w-0 rounded-lg border bg-background px-2 py-1 text-sm font-semibold" bind:value={it.titre} oninput={toucher} aria-label="Titre {i + 1}" />
              <textarea class="rounded-lg border bg-background px-2 py-1 text-sm [field-sizing:content] min-h-14" rows="2" bind:value={it.texte} oninput={toucher} aria-label="Texte {i + 1}"></textarea>
              {@render compteur(`p2:${i}`)}
              <IaBloc bind:this={ias[`p2:${i}`]} nom="Page 2, article {i + 1}" pid={id} texte={() => it.texte} actions={['titres', 'raccourcir', 'journal', 'traduire']} signes={cible(`p2:${i}`, it.texte)}
                      onapply={(a, t) => { if (a === 'titres') it.titre = t; else it.texte = t; toucher() }} />
              {#if ouvert?.bloc === 'p2' && ouvert.index === i}<Propositions liste={evts} choisis={pris} tient={tient(`p2:${i}`)} onchoisir={(f) => choisir('p2', f, i)} onfermer={() => (ouvert = null)} />{/if}
              </div>
              </Element>
            </li>
          {/each}
        </ul>
      </section>

      <!-- Page 3 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4 {cadrePage(3)}" class:hidden={!aFaire('chrono', 'musique', 'cinema', 'nes', 'morts')} aria-label="Chronologie">
        <div class="mb-2 flex items-center justify-between"><h2 class="etiquette">Page 3 · chronologie de l'année</h2>{@render bouton('chrono', null, 'Ajouter')}</div>
        {#if ouvert?.bloc === 'chrono' && ouvert.index === null}<Propositions liste={annee} choisis={pris} onchoisir={(f) => choisir('chrono', f, null)} onfermer={() => (ouvert = null)} />{/if}
        <ul class="grid gap-2">
          {#each contenu.chrono as c, i}
            <li class="{c.masque ? 'opacity-45' : ''}">
              <Element cle="chrono:{c.id ?? i}" page={3} titre="Repère {i + 1}" valeur={{ q: c.quand, x: c.texte, m: !!c.masque }}
                       onia={() => ias[`chrono:${i}`]?.tout()} onchanger={() => ouvrir('chrono', i)} changer="Un autre repère"
                       onrefuser={() => { contenu.chrono.splice(i, 1); toucher() }}>
              <div class="grid gap-1 {cadre(`chrono:${i}`)}">
              <div class="flex flex-wrap items-center gap-2 sm:flex-nowrap">
                <input class="w-20 shrink-0 rounded-lg border bg-background px-2 py-1 text-xs" bind:value={c.quand} oninput={toucher} aria-label="Date du repère {i + 1}" />
                <input class="order-last min-w-0 flex-1 basis-full sm:order-none sm:basis-0 rounded-lg border bg-background px-2 py-1 text-sm" bind:value={c.texte} oninput={toucher} aria-label="Repère {i + 1}" />
              </div>
              {@render compteur(`chrono:${i}`)}
              <IaBloc bind:this={ias[`chrono:${i}`]} nom="Repère {i + 1}" pid={id} texte={() => c.texte} actions={['raccourcir', 'journal', 'traduire']} signes={cible(`chrono:${i}`, c.texte)}
                      onapply={(a, t) => { c.texte = t; toucher() }} />
              {#if ouvert?.bloc === 'chrono' && ouvert.index === i}<Propositions liste={annee} choisis={pris} tient={tient(`chrono:${i}`)} onchoisir={(f) => choisir('chrono', f, i)} onfermer={() => (ouvert = null)} />{/if}
              </div>
              </Element>
            </li>
          {/each}
        </ul>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
          <span class="etiquette">Culture de l'année</span>
          <Button variant="outline" size="sm" onclick={remplirCulture}>Remplir depuis le top 5</Button>
        </div>
        {#if d.livret.propositions.culture}
          {@const top = d.livret.propositions.culture}
          <details class="mt-1 text-xs text-muted-foreground"><summary class="cursor-pointer">Top 5 de l'année</summary>
            <div class="mt-2 grid gap-2 sm:grid-cols-3">
              {#each [['Film', 'Films'], ['Serie', 'Séries'], ['Musique', 'Musique']] as [cat, nom]}
                <div>
                  <p class="font-medium text-foreground">{nom}</p>
                  <ol class="mt-1 grid gap-0.5">
                    {#each top[cat] ?? [] as x}
                      <li>{x.rang}. {x.titre}{x.createur ? ' — ' + x.createur : ''}
                        {#if x.provisoire}<span class="text-primary"> (provisoire)</span>{/if}
                        {#if x.metrique.includes('à vérifier')}<span class="text-destructive"> (à vérifier)</span>{/if}</li>
                    {:else}<li>—</li>{/each}
                  </ol>
                </div>
              {/each}
            </div>
          </details>
        {/if}
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          {#each [['musique', 'Musique', "n°1 des ventes de la semaine (vide : rubrique absente)"], ['cinema', 'Cinéma', "films à l'affiche (vide : rubrique absente)"]] as [cle, nom, aide]}
            <Element {cle} page={3} titre={nom} valeur={contenu[cle] ?? ''} onchanger={remplirCulture} changer="Depuis le top 5"
                     onrefuser={contenu[cle] ? () => { contenu[cle] = ''; toucher() } : null}>
              <textarea rows="3" class="min-w-0 rounded-lg border bg-background px-2 py-1 text-sm {bord(cle)}" bind:value={contenu[cle]} oninput={toucher} placeholder={aide} aria-label={nom}></textarea>{@render compteur(cle)}
            </Element>
          {/each}
        </div>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          {#each [['nes', 'Nés le même jour'], ['morts', 'Disparus le même jour']] as [cle, libelle]}
            <Element {cle} page={3} titre={libelle} valeur={contenu[cle].map((p) => [p.nom, !!p.masque])}>
              <ul class="grid gap-1 text-sm">
                {#each contenu[cle] as p}
                  <li class="flex items-center justify-between gap-2 {p.masque ? 'opacity-45' : ''}"><span>{p.nom} ({p.annee})</span>{@render masquer(p)}</li>
                {/each}
              </ul>
              {#if (d.livret.propositions[cle] ?? []).length > contenu[cle].length}
                <details class="mt-1 text-xs text-muted-foreground"><summary class="cursor-pointer">Ajouter</summary>
                  <ul class="mt-1 grid gap-0.5">
                    {#each d.livret.propositions[cle].filter((p) => !contenu[cle].some((x) => x.nom === p.nom)) as p}
                      <li><button type="button" class="hover:text-foreground" onclick={() => { contenu[cle] = [...contenu[cle], { nom: p.nom, annee: p.annee }]; toucher() }}>
                        <Plus class="inline size-3" aria-hidden="true" /> {p.nom} ({p.annee})</button></li>
                    {/each}
                  </ul>
                </details>
              {/if}
            </Element>
          {/each}
        </div>
      </section>

      <!-- Page 4 -->
      <section class="min-w-0 rounded-2xl border bg-card p-4 {cadrePage(4)}" class:hidden={!aFaire('mot', 'photo', 'code')} aria-label="Le mot des hôtes">
        <h2 class="etiquette mb-2">Page 4 · le mot des hôtes</h2>
        <Element cle="mot" page={4} titre="Le mot des hôtes" valeur={mot} onia={() => ias.mot?.tout()}
                 onchanger={() => { mot = d.livret.mot_defaut; toucher() }} changer="Mot par défaut">
        <textarea class="w-full rounded-lg border bg-background px-3 py-2 font-serif {bord('mot')}" rows="8" bind:value={mot} oninput={toucher} aria-label="Mot des hôtes"></textarea>
        {@render compteur('mot')}
        <IaBloc bind:this={ias.mot} nom="Le mot des hôtes" pid={id} texte={() => mot} actions={['mot', 'raccourcir']} signes={cible('mot', mot)} onapply={(a, t) => { mot = t; toucher() }} />
        <p class="mt-1 text-xs text-muted-foreground">Une ligne vide sépare les paragraphes. Signature : « {d.signature} » (Réglages › Le journal). L'IA s'appuie sur les événements racontés dans la Gazette.</p>
        </Element>

        <!-- 0.13 : photo d'Immich, imprimée en noir et blanc au-dessus du mot -->
        <div class="mt-3"></div>
        <Element cle="photo" page={4} titre="Photo de la page 4" valeur={{ i: photo.id ?? '', c: photo.cadrage ?? 'haut', l: photo.legende ?? '' }}
                 onia={photo.id ? legendeEnFile : null} onchanger={d.livret.photos_choix.length ? photoSuivante : null} changer="Une autre photo"
                 onrefuser={photo.id ? () => { photo = {}; propsLegende = []; ctxPhoto = null; toucher() } : null}>
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="etiquette">Photo (noir et blanc, au-dessus du mot)</h3>
          {#if d.livret.immich}
            <button type="button" class="text-xs text-muted-foreground hover:text-foreground disabled:opacity-50" disabled={demande !== ''} onclick={chercherPhotos}>
              {demande === 'photos' ? '…' : d.livret.photos_choix.length ? 'Chercher de nouveau' : 'Chercher dans Immich'}</button>
          {/if}
        </div>
        {#if !d.livret.immich}
          <p class="text-xs text-muted-foreground">Immich n'est pas réglé (GAZETTE_IMMICH_CLE) : page 4 sans photo.</p>
        {:else if !d.livret.photos_choix.length}
          <p class="text-xs text-muted-foreground">Aucune photo proposée (personne d'Immich liée dans carnet ?) : page 4 sans photo.</p>
        {:else}
          <div class="mt-2 grid grid-cols-3 gap-2" role="radiogroup" aria-label="Photo de la page 4">
            {#each d.livret.photos_choix as x}
              <button type="button" role="radio" aria-checked={photo.id === x.id} onclick={() => prendrePhoto(x)}
                      class="relative aspect-[4/3] overflow-hidden rounded-lg border-2 {photo.id === x.id ? 'border-primary' : 'border-transparent opacity-80 hover:opacity-100'}">
                <img alt="Photo du {dateCourte(x.date)}" src={`/api/livrets/${id}/photos/${x.id}`} class="size-full object-cover grayscale" loading="lazy" />
                <span class="absolute right-1 bottom-1 rounded bg-black/70 px-1 text-[0.65rem] text-white">{x.date?.slice(0, 4)}</span>
              </button>
            {/each}
          </div>
          <p class="mt-1 text-xs text-muted-foreground">{photo.id ? 'Toucher la photo choisie la retire.' : 'Aucune photo choisie : page 4 sans photo.'}</p>
          {#if photo.id}
            <div class="mt-2 flex flex-wrap gap-1.5 text-xs" role="radiogroup" aria-label="Cadrage">
              {#each Object.entries(d.livret.cadrages) as [cle, nom]}
                <button type="button" role="radio" aria-checked={(photo.cadrage ?? 'haut') === cle} onclick={() => { photo.cadrage = cle; toucher() }}
                        class="rounded-full border px-2 py-0.5 {(photo.cadrage ?? 'haut') === cle ? 'border-primary bg-primary/15' : ''}">{nom}</button>
              {/each}
            </div>
            <label class="mt-2 grid gap-1 text-sm">
              <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Légende imprimée</span>
              <input class="min-w-0 rounded-lg border bg-background px-2 py-1 italic" maxlength="160" bind:value={photo.legende} oninput={toucher} placeholder="(vide : pas de légende)" />
            </label>
            <div class="mt-2 grid min-w-0 gap-1.5 rounded-lg border border-dashed p-2">
              <span class="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">Pour l'IA (non imprimé)</span>
              <div class="flex min-w-0 flex-wrap items-center justify-end gap-2">
                <input class="w-full min-w-0 rounded-lg border bg-background px-2 py-1 text-sm" maxlength="400" bind:value={photo.description} oninput={toucher}
                       placeholder="Décris la photo (l'IA proposera 5 légendes façon journal de l'époque)" aria-label="Description de la photo" />
                <Button size="sm" variant="outline" class="shrink-0" onclick={legendeEnFile} disabled={demande === 'legende'}>
                  <Sparkles class="size-3.5" aria-hidden="true" />{demande === 'legende' ? '…' : '5 légendes'}</Button>
              </div>
              {#if ctxTexte(ctxPhoto)}<p class="text-[0.7rem] break-words text-muted-foreground">Immich · {ctxTexte(ctxPhoto)}</p>{/if}
              {#if propsLegende.length}
                <ul class="grid gap-1" aria-label="Légendes proposées">
                  {#each propsLegende as t}
                    <li><button type="button" class="w-full rounded-md px-2 py-1 text-left text-sm break-words italic hover:bg-secondary" onclick={() => { photo.legende = t; toucher() }}>« {t} »</button></li>
                  {/each}
                </ul>
              {/if}
            </div>
          {/if}
        {/if}
        </Element>

        <div class="mt-3"></div>
        <Element cle="code" page={4} titre="Code-barres" valeur={codeBarres} onchanger={() => { codeBarres = ''; toucher() }} changer="Message par défaut">
        <label class="grid gap-1 text-sm">
          <span class="etiquette">Code-barres (message caché, 30 caractères)</span>
          <input class="min-w-0 rounded-lg border bg-background px-2 py-1" maxlength="30" bind:value={codeBarres} oninput={toucher} placeholder={d.livret.code_barres_defaut} />
          <span class="text-xs text-muted-foreground">Lisible par une appli de scan ; rien n'est écrit sous les barres. Vide : « {d.livret.code_barres_defaut} ».</span>
        </label>
        </Element>
      </section>

      <!-- Fiche et gestes -->
      <section class="min-w-0 rounded-2xl border bg-card p-4" aria-label="Fiche">
        <div class="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onclick={() => (ficheOuverte = !ficheOuverte)}>Modifier la fiche</Button>
          <Button variant="outline" size="sm" onclick={() => preparer(false)} disabled={d.livret.etat === 'en_preparation'}>Préparer de nouveau</Button>
          <Button variant="outline" size="sm" onclick={() => preparer(true)} disabled={d.livret.etat === 'en_preparation'}>Relire les sources</Button>
          <Button variant="ghost" size="sm" class="text-destructive" onclick={supprimer}>Supprimer</Button>
        </div>
        {#if ficheOuverte}<div class="mt-4"><FicheForm valeur={d.personne} bouton="Enregistrer la fiche" onvalider={modifierFiche} onannuler={() => (ficheOuverte = false)} /></div>{/if}
        <details class="mt-4 text-sm">
          <summary class="cursor-pointer text-muted-foreground">Séjours d'avant Gazette {d.personne.sejours_avant ? `(${d.personne.sejours_avant})` : ''}</summary>
          <p class="mt-2 text-xs text-muted-foreground">La Gazette sert au premier séjour ; à partir du deuxième, La Récidive (journal à scandale) la remplace, avec les photos prises depuis le séjour précédent. Note ici les séjours d'avant l'installation de Gazette.</p>
          <div class="mt-2 flex flex-wrap items-end gap-3">
            <label class="grid gap-1"><span class="etiquette">Nombre</span>
              <input type="number" min="0" max="99" class="w-24 rounded-lg border bg-background px-2 py-1" bind:value={avant.sejours_avant} /></label>
            <label class="grid gap-1"><span class="etiquette">Arrivée du dernier</span>
              <input type="date" class="rounded-lg border bg-background px-2 py-1" bind:value={avant.dernier_avant} /></label>
            <Button size="sm" variant="outline" onclick={enregistrerAvant}>Enregistrer</Button>
          </div>
        </details>
        {#if contenu.notes?.length}<p class="mt-3 text-xs text-muted-foreground">Sources en défaut : {contenu.notes.join(' ; ')}</p>{/if}
      </section>
      </div>
    </div>

    <!-- Aperçu -->
    <aside class="lg:sticky lg:top-6 lg:self-start" aria-label="Aperçu">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 class="etiquette">Aperçu{modifie ? ' (enregistre pour mettre à jour)' : ''}</h2>
        <span class="flex gap-3 text-xs">
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/livrets/${id}/pdf?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
          <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`/api/livrets/${id}/pdf?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
        </span>
      </div>
      <div class="max-h-[78vh] overflow-y-auto rounded-xl border" bind:clientWidth={largeur}>
        <div style="height:{Math.round(3480 * echelle)}px;position:relative;overflow:hidden">
          <iframe title="Aperçu du livret" src={`/api/livrets/${id}/apercu?mode=ecran&t=${tampon}`} scrolling="no"
                  style="position:absolute;top:0;left:0;width:600px;height:3480px;border:0;transform:scale({echelle});transform-origin:0 0"></iframe>
        </div>
      </div>
      <p class="mt-2 text-xs text-muted-foreground">Impression : A4 paysage, recto-verso bord court, puis plier en deux.</p>
    </aside>
  </div>
{:else if message}
  <p class="text-sm text-destructive" role="alert">{message}</p>
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
