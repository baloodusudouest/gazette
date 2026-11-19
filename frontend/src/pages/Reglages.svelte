<script>
  // « Réglages » : le journal (réglages d'usage, sauvegardés chaque nuit par l'Anneau), Restaurer les réglages,
  // le top 5 culturel, les règles, le journal des gestes, la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()
  let r = $state(null)
  let c = $state(null)
  let message = $state('')
  let copie = $state(false)
  let voirPrompt = $state(false)
  const GESTES = { preparation: 'livret préparé', approuver: 'livret approuvé', fiche: 'fiche', erreur: 'échec de préparation', culture: 'top 5 culturel', reglages: 'réglages' }

  let j = $state(null)
  let modifie = $state(false)
  let messageJ = $state('')
  let envoiJ = $state(false)
  // 0.27 : envois vers carnet (séjours, Gazettes, Récidives, photos scandale) et file de nouvel essai
  let envois = $state({ attente: null, message: '', encours: false })
  async function lireEnvois() {
    try { envois.attente = (await api.get('/api/carnet/envois')).en_attente } catch { envois.attente = null }
  }
  async function toutEnvoyer() {
    envois.encours = true; envois.message = ''
    try {
      const r2 = await api.post('/api/carnet/envoyer-tout', {})
      envois.message = `${r2.sejours} séjour(s), ${r2.gazettes} Gazette(s), ${r2.recidives} Récidive(s) envoyés`
        + (r2.en_attente ? ` ; ${r2.en_attente} envoi(s) en attente (carnet injoignable ou trop ancien).` : '.')
      await lireEnvois()
    } catch (err) { envois.message = err.message } finally { envois.encours = false }
  }
  async function lire() {
    lireEnvois()
    try {
      r = await api.get('/api/reglages'); c = await api.get('/api/culture')
      j = { ...r.journal }; modifie = false
    } catch { /* déconnecté */ }
  }
  async function enregistrerJournal(e) {
    e.preventDefault()
    envoiJ = true; messageJ = ''
    try { await api.put('/api/reglages', $state.snapshot(j)); await lire(); messageJ = 'Enregistré : vaut aussitôt pour tous les aperçus et les PDF.' }
    catch (err) { messageJ = err.message }
    envoiJ = false
  }
  async function importer(e) {
    const f = e.currentTarget.files?.[0]
    e.currentTarget.value = ''
    if (!f) return
    message = ''
    try {
      const etat = await api.post('/api/culture/import', { texte: await f.text() })
      message = `Fichier importé : ${etat.lignes} lignes, ${etat.annees[0]} à ${etat.annees[1]}. Les livrets déjà préparés gardent leur texte ; « Remplir depuis le top 5 » dans un livret le met à jour.`
      await lire()
    } catch (err) { message = err.message }
  }
  async function revenir() {
    if (!confirm('Revenir au fichier livré avec l\'appli ? Le fichier importé est retiré.')) return
    await api.post('/api/culture/revenir')
    message = 'Version livrée avec l\'appli rétablie.'
    await lire()
  }
  async function copier() {
    try { await navigator.clipboard.writeText(c.prompt); copie = true; setTimeout(() => (copie = false), 2000) }
    catch { voirPrompt = true }
  }

  // Restaurer les réglages : dates gardées par l'Anneau → différences (avant → sauvegardé) → confirmer
  let rest = $state({ ouvert: false, dates: [], le: '', diff: null, version: '', message: '', attente: false })
  function valeur(v) {
    if (typeof v === 'boolean') return v ? 'oui' : 'non'
    if (v === null || v === undefined || v === '') return '(vide)'
    const s = String(v)
    return s.length > 80 ? s.slice(0, 79) + '…' : s
  }
  async function ouvrirRestaurer() {
    rest = { ouvert: true, dates: [], le: '', diff: null, version: '', message: '', attente: true }
    try { rest.dates = (await api.get('/api/restaurer')).dates; rest.le = rest.dates[0] ?? ''; if (rest.le) await voirDifferences() }
    catch (err) { rest.message = err.message }
    rest.attente = false
  }
  async function voirDifferences() {
    rest.diff = null; rest.message = ''; rest.attente = true
    try { const v = await api.get('/api/restaurer?le=' + encodeURIComponent(rest.le)); rest.diff = v.differences; rest.version = v.version }
    catch (err) { rest.message = err.message }
    rest.attente = false
  }
  async function confirmerRestaurer() {
    rest.attente = true; rest.message = ''
    try {
      const r2 = await api.post('/api/restaurer', { le: rest.le })
      await lire()
      rest.diff = []
      rest.message = r2.restaures.length ? `Réglages du ${rest.le.split('-').reverse().join('/')} remis : ${r2.restaures.length} changé${r2.restaures.length > 1 ? 's' : ''}.` : (r2.message ?? 'Rien à restaurer.')
    } catch (err) { rest.message = err.message }
    rest.attente = false
  }
  // 0.20 : simuler la Gazette ou La Récidive d'une personne (numéro d'essai à part, jamais compté)
  // 0.24 : la personne se choisit dans les contacts de carnet (sa fiche de Gazette sert si elle existe) ;
  // sans carnet réglé, parmi les fiches de Gazette comme avant.
  let sim = $state({ carnet: true, personnes: [], essais: [], q: '', propositions: [], contact: null, personne: '', journal: 'recidive', message: '', attente: false })
  let minuteurSim = null
  async function lireEssais() {
    try {
      const [l, e, c2] = await Promise.all([api.get('/api/livrets'), api.get('/api/essais'), api.get('/api/carnet/suggestions')])
      sim.personnes = l.livrets.map((x) => ({ id: x.id, nom: x.nom }))
      sim.essais = e.essais
      sim.carnet = c2.actif
    } catch { /* déconnecté */ }
  }
  function chercherContact() {
    clearTimeout(minuteurSim)
    sim.contact = null
    minuteurSim = setTimeout(async () => {
      try { sim.propositions = sim.q.trim().length >= 2 ? (await api.get(`/api/carnet/suggestions?q=${encodeURIComponent(sim.q.trim())}`)).suggestions : [] }
      catch { sim.propositions = [] }
    }, 250)
  }
  function prendreContact(c2) {
    sim.contact = c2; sim.q = c2.nom; sim.propositions = []
  }
  async function simuler() {
    sim.attente = true; sim.message = ''
    try {
      const corps = sim.carnet ? { carnet_id: sim.contact.carnet_id, journal: sim.journal } : { personne_id: +sim.personne, journal: sim.journal }
      location.hash = (await api.post('/api/essais', corps)).lien
    }
    catch (err) { sim.message = err.message }
    sim.attente = false
  }
  async function supprimerEssai(x) {
    await api.del(`/api/essais/${x.journal}/${x.id}`)
    await lireEssais()
  }
  // 0.25 : banque d'inspiration (rumeurs, horoscopes, mots des hôtes, titres) importée d'un fichier texte
  let banq = $state({ comptes: null, noms: {}, message: '', attente: false })
  async function lireBanque() {
    try { const r = await api.get('/api/banque'); banq.comptes = r.comptes; banq.noms = r.noms } catch { /* déconnecté */ }
  }
  async function importerBanque(e) {
    const fichiers = [...(e.currentTarget.files ?? [])]
    e.currentTarget.value = ''
    if (!fichiers.length) return
    banq.attente = true; banq.message = ''
    const lignes = []
    for (const f of fichiers) {
      try {
        const r = await api.post('/api/banque/import', { texte: await f.text(), source: f.name })
        banq.comptes = r.comptes
        const ajout = Object.entries(r.ajoutes).filter(([, n]) => n).map(([k, n]) => `${n} ${banq.noms[k]?.toLowerCase() ?? k}`).join(', ')
        const ecarts = Object.entries(r.ecartes).map(([k, n]) => `${n} ${k}`).join(', ')
        lignes.push(`${f.name} : ${ajout || 'rien de neuf'}${r.deja ? ` ; ${r.deja} déjà dans la banque` : ''}${ecarts ? ` ; écartés : ${ecarts}` : ''}.`)
      } catch (err) { lignes.push(`${f.name} : ${err.message}`) }
    }
    banq.message = lignes.join(' ')
    banq.attente = false
  }
  async function viderBanque(sorte) {
    const quoi = sorte ? banq.noms[sorte]?.toLowerCase() : 'toute la banque'
    if (!confirm(`Vider ${quoi} ? (Exporte d'abord si tu veux garder une copie.)`)) return
    try { const r = await api.del(`/api/banque${sorte ? `?sorte=${sorte}` : ''}`); banq.comptes = r.comptes; banq.message = `${r.retires} texte(s) retiré(s).` }
    catch (err) { banq.message = err.message }
  }
  onMount(() => { lire(); lireEssais(); lireBanque() })
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Réglages</h1>
</header>

<section class="mb-4 rounded-2xl border border-primary/50 bg-card p-5" aria-label="Simuler">
  <h2 class="text-lg font-semibold">Simuler un journal</h2>
  <p class="mt-1 text-sm text-muted-foreground">Pour essayer les réglages : un numéro d'essai à part pour un contact de carnet (sa fiche de Gazette sert si elle existe ; sinon une fiche d'essai est faite d'après carnet et part avec l'essai). La Gazette demande une date de naissance complète. Il ne compte jamais (N°, déjà paru, carnet, archives, Home Assistant) et se supprime d'un bouton.</p>
  <div class="mt-3 flex flex-wrap items-center gap-2">
    {#if sim.carnet}
      <div class="relative min-w-0 flex-1 sm:max-w-xs">
        <input class="h-10 w-full rounded-lg border bg-background px-3 text-sm" bind:value={sim.q} oninput={chercherContact}
               placeholder="Chercher dans carnet…" autocomplete="off" aria-label="Contact de carnet" />
        {#if sim.propositions.length}
          <ul class="absolute z-10 mt-1 grid w-full gap-0.5 rounded-xl border bg-background p-1 shadow-lg" aria-label="Contacts de carnet">
            {#each sim.propositions as c2 (c2.carnet_id ?? c2.nom)}
              <li><button type="button" onclick={() => prendreContact(c2)} class="w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-secondary">
                {c2.nom}{#if !c2.naissance}<span class="text-muted-foreground"> · date incomplète</span>{/if}</button></li>
            {/each}
          </ul>
        {/if}
      </div>
    {:else}
      <select class="h-10 min-w-0 flex-1 rounded-lg border bg-background px-2 text-sm sm:max-w-xs" bind:value={sim.personne} aria-label="Personne">
        <option value="">Choisir une personne…</option>
        {#each sim.personnes as p}<option value={p.id}>{p.nom}</option>{/each}
      </select>
    {/if}
    <div class="flex gap-1.5" role="radiogroup" aria-label="Journal à simuler">
      {#each [['gazette', 'La Gazette'], ['recidive', 'La Récidive']] as [cle, nom]}
        <button type="button" role="radio" aria-checked={sim.journal === cle} onclick={() => (sim.journal = cle)}
                class="rounded-full border px-3 py-1.5 text-sm aria-checked:border-primary aria-checked:bg-primary aria-checked:text-primary-foreground">{nom}</button>
      {/each}
    </div>
    <Button onclick={simuler} disabled={(sim.carnet ? !sim.contact : !sim.personne) || sim.attente}>{sim.attente ? 'Création…' : 'Simuler'}</Button>
  </div>
  {#if sim.message}<p class="mt-2 text-sm text-destructive" role="alert">{sim.message}</p>{/if}
  {#if sim.essais.length}
    <ul class="mt-3 grid gap-1.5 text-sm" aria-label="Essais en cours">
      {#each sim.essais as x (x.journal + x.id)}
        <li class="flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-1.5">
          <a class="hover:text-primary" href={x.lien}>{x.journal === 'recidive' ? `La Récidive N° ${x.numero}` : 'La Gazette'} d'essai · {x.nom}</a>
          <button type="button" class="text-xs text-muted-foreground hover:text-destructive" onclick={() => supprimerEssai(x)}>Supprimer</button>
        </li>
      {/each}
    </ul>
  {/if}
</section>

{#if r}
  {#if j}
    <form class="rounded-2xl border bg-card p-5" aria-label="Le journal" onsubmit={enregistrerJournal}>
      <h2 class="text-lg font-semibold">Le journal</h2>
      <p class="mt-1 text-sm text-muted-foreground">Ce qui est commun à tous les livrets. Un mot des hôtes déjà écrit dans un livret est gardé ; les autres prennent le mot par défaut.</p>
      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        {#each ['titre', 'sous_titre', 'lieu', 'lieu_detail', 'chez', 'signature'] as cle}
          {@const ch = r.champs[cle]}
          <label class="grid gap-1 text-sm">
            <span class="text-muted-foreground">{ch.libelle}</span>
            <input class="h-10 rounded-lg border bg-background px-3" maxlength={ch.maxi} bind:value={j[cle]} oninput={() => (modifie = true)} />
            <span class="text-xs text-muted-foreground">{ch.aide}</span>
          </label>
        {/each}
        <label class="grid gap-1 text-sm sm:col-span-2">
          <span class="text-muted-foreground">{r.champs.mot_modele.libelle}</span>
          <textarea rows="6" class="rounded-lg border bg-background px-3 py-2 font-serif" maxlength={r.champs.mot_modele.maxi} bind:value={j.mot_modele} oninput={() => (modifie = true)}></textarea>
          <span class="text-xs text-muted-foreground">{r.champs.mot_modele.aide}</span>
        </label>
        <label class="flex items-center gap-3 text-sm">
          <input type="color" class="h-9 w-12 rounded border bg-background" bind:value={j.accent} oninput={() => (modifie = true)} />
          <span><span class="text-muted-foreground">{r.champs.accent.libelle}</span> · {j.accent}</span>
        </label>
        <label class="flex items-center gap-3 text-sm">
          <input type="checkbox" bind:checked={j.larousse} onchange={() => (modifie = true)} />
          <span>Utiliser Larousse, Journaux de l'année (1966-2003)</span>
        </label>
      </div>

      <!-- 0.18 : réglages généraux de La Récidive (journal à scandale dès le 2e séjour) -->
      <h3 class="mt-6 text-base font-semibold">La Récidive</h3>
      <p class="mt-1 text-sm text-muted-foreground">Le journal à scandale qui remplace la Gazette à partir du deuxième séjour. Valeurs par défaut des nouvelles éditions ; chaque édition reste modifiable.</p>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        {#each ['r_titre', 'r_accroche_femme', 'r_accroche_homme', 'r_accroche_autre'] as cle}
          {@const ch = r.champs[cle]}
          <label class="grid gap-1 text-sm">
            <span class="text-muted-foreground">{ch.libelle}</span>
            <input class="h-10 rounded-lg border bg-background px-3" maxlength={ch.maxi} bind:value={j[cle]} oninput={() => (modifie = true)} />
            <span class="text-xs text-muted-foreground">{ch.aide}</span>
          </label>
        {/each}
        <label class="grid gap-1 text-sm sm:col-span-2">
          <span class="text-muted-foreground">{r.champs.r_mot_modele.libelle}</span>
          <textarea rows="5" class="rounded-lg border bg-background px-3 py-2 font-serif" maxlength={r.champs.r_mot_modele.maxi} bind:value={j.r_mot_modele} oninput={() => (modifie = true)}></textarea>
          <span class="text-xs text-muted-foreground">{r.champs.r_mot_modele.aide}</span>
        </label>
      </div>

      <!-- 0.22 : second modèle de l'IA du PC (« Autres propositions ») -->
      <h3 class="mt-6 text-base font-semibold">L'IA du PC</h3>
      <p class="mt-1 text-sm text-muted-foreground">Le premier jet vient du modèle de la stack ; le bouton « Autres propositions » redemande la même chose à un second modèle.</p>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        <label class="grid gap-1 text-sm">
          <span class="text-muted-foreground">{r.champs.modele_second.libelle}</span>
          <input class="h-10 rounded-lg border bg-background px-3 font-mono" maxlength={r.champs.modele_second.maxi} bind:value={j.modele_second}
                 oninput={() => (modifie = true)} placeholder="(vide : pas de bouton)" spellcheck="false" autocomplete="off" />
          <span class="text-xs text-muted-foreground">{r.champs.modele_second.aide}</span>
        </label>
      </div>
      <div class="mt-4 flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={!modifie || envoiJ}>Enregistrer</Button>
        {#if !modifie && !messageJ}<span class="text-xs text-muted-foreground">rien à enregistrer</span>{/if}
        {#if messageJ}<span class="text-sm" role="status">{messageJ}</span>{/if}
      </div>
      <p class="mt-3 text-xs text-muted-foreground">Impression : {r.lecture_seule ? `lecture seule (${r.lecture_seule_origine === 'maison' ? 'toute la maison' : 'cette appli'}), rien ne part à l'imprimante` : 'à venir (temps 3) ; PDF à imprimer pour l\'instant'}.</p>
    </form>
  {/if}

  <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Banque d'inspiration">
    <h2 class="text-lg font-semibold">Banque d'inspiration</h2>
    <p class="mt-1 text-sm text-muted-foreground">Rumeurs, horoscopes, mots des hôtes, titres scandale et courrier des lecteurs importés d'un fichier texte. Le bouton « Banque » des éditeurs y pioche des propositions (même sans l'IA du PC) ; l'IA en reçoit quelques-unes comme exemples de ton. Rien n'est imprimé sans ton choix, et rien ne revient deux fois pour la même personne.</p>
    {#if banq.comptes}
      <ul class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Contenu de la banque">
        {#each Object.entries(banq.comptes) as [sorte, n]}
          <li class="flex min-w-0 flex-col rounded-lg border bg-background px-3 py-2">
            <span class="text-2xl font-semibold tabular-nums">{n}</span>
            <span class="text-xs text-muted-foreground">{banq.noms[sorte]}</span>
            {#if n}<button type="button" class="mt-1 self-start text-[0.7rem] text-muted-foreground underline-offset-4 hover:text-destructive hover:underline" onclick={() => viderBanque(sorte)}>Vider</button>{/if}
          </li>
        {/each}
      </ul>
    {/if}
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <label class="inline-flex h-10 cursor-pointer items-center rounded-lg border bg-background px-4 text-sm font-medium hover:bg-secondary {banq.attente ? 'pointer-events-none opacity-50' : ''}">
        {banq.attente ? 'Import…' : 'Importer un fichier'}
        <input type="file" accept=".txt,.md,text/plain,text/markdown" multiple class="sr-only" onchange={importerBanque} aria-label="Fichier de la banque" />
      </label>
      <a class="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" href="/api/banque/export">Exporter</a>
      {#if banq.comptes && Object.values(banq.comptes).some(Boolean)}
        <button type="button" class="text-sm text-muted-foreground underline-offset-4 hover:text-destructive hover:underline" onclick={() => viderBanque('')}>Tout vider</button>
      {/if}
    </div>
    <p class="mt-2 text-xs text-muted-foreground">Format : sections « # RUMEURS », « # HOROSCOPES », « # MOTS », « # TITRES », « # COURRIER », puis une ligne « - texte » par élément (courrier : « lettre ::: signature ::: réponse »). Balises : {'{prenom}'}, {'{salut}'} (« Chère Camille »), {'{chez}'}, {'{il}'} (il / elle), {'{e}'} (accord). Les doublons sont ignorés : tu peux réimporter sans risque.</p>
    {#if banq.message}<p class="mt-2 text-sm" role="status">{banq.message}</p>{/if}
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Envois vers carnet">
    <h2 class="text-lg font-semibold">Envois vers carnet</h2>
    <p class="mt-1 text-sm text-muted-foreground">Gazette envoie à carnet chaque séjour, chaque Gazette et Récidive approuvée, et le nombre de photos « scandale » de chaque personne (toutes les 6 heures) : carnet les range dans la fiche et le coffre Contacts. Un envoi raté est réessayé toutes les 10 minutes.</p>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      <Button variant="outline" disabled={envois.encours} onclick={toutEnvoyer}>{envois.encours ? 'Envoi…' : 'Tout envoyer à carnet'}</Button>
      {#if envois.attente}<span class="text-sm text-muted-foreground">{envois.attente.length ? `${envois.attente.length} envoi(s) en attente` : 'aucun envoi en attente'}</span>{/if}
    </div>
    {#if envois.attente?.length}
      <ul class="mt-2 grid gap-1 text-xs text-muted-foreground">
        {#each envois.attente.slice(0, 5) as e (e.id)}<li>{e.quoi} — {e.erreur} ({e.essais} essai{e.essais > 1 ? 's' : ''})</li>{/each}
      </ul>
    {/if}
    {#if envois.message}<p class="mt-2 text-sm" role="status">{envois.message}</p>{/if}
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Restaurer les réglages">
    <h2 class="text-lg font-semibold">Restaurer les réglages</h2>
    <p class="mt-1 text-sm text-muted-foreground">L'Anneau garde chaque nuit une copie des réglages du journal (rien d'autre : ni fiches, ni livrets, ni mot de passe). Choisis une date, vérifie ce qui changerait, puis confirme.</p>
    {#if !rest.ouvert}
      <div class="mt-3"><Button variant="outline" onclick={ouvrirRestaurer}>Restaurer les réglages</Button></div>
    {:else}
      {#if rest.dates.length}
        <label class="mt-3 grid max-w-xs gap-1 text-sm">
          <span class="text-muted-foreground">Sauvegarde du</span>
          <select class="h-10 rounded-lg border bg-background px-3" bind:value={rest.le} onchange={voirDifferences} disabled={rest.attente}>
            {#each rest.dates as d}<option value={d}>{d.split('-').reverse().join('/')}</option>{/each}
          </select>
        </label>
      {/if}
      {#if rest.diff && rest.diff.length}
        <ul class="mt-3 grid gap-2 text-sm" aria-label="Différences">
          {#each rest.diff as d}
            <li class="min-w-0 rounded-lg border bg-background px-3 py-2">
              <span class="block text-muted-foreground">{r.libelles?.[d.cle] ?? d.cle}</span>
              <span class="block break-words"><span class="text-muted-foreground line-through">{valeur(d.actuel)}</span> → {valeur(d.sauve)}</span>
            </li>
          {/each}
        </ul>
        <div class="mt-3 flex flex-wrap items-center gap-3">
          <Button onclick={confirmerRestaurer} disabled={rest.attente}>Remettre ces réglages</Button>
          <span class="text-xs text-muted-foreground">sauvegarde faite par Gazette {rest.version || '?'}</span>
        </div>
      {:else if rest.diff && !rest.message}
        <p class="mt-3 text-sm text-muted-foreground">Rien à restaurer : les réglages actuels sont ceux de cette sauvegarde.</p>
      {/if}
      {#if rest.attente}<p class="mt-3 text-sm text-muted-foreground" role="status">Lecture chez l'Anneau…</p>{/if}
      {#if rest.message}<p class="mt-3 text-sm" role="status">{rest.message}</p>{/if}
    {/if}
  </section>

  {#if c}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Top 5 culturel">
      <h2 class="text-lg font-semibold">Top 5 culturel</h2>
      <p class="mt-1 text-sm text-muted-foreground">Films, séries et musique de chaque année : la page 3 du livret (Musique, Cinéma) s'en sert. Préparé avec Claude, puis importé ici.</p>
      <dl class="mt-3 grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
        <dt class="text-muted-foreground">Fichier</dt><dd>{c.source}{c.importe_le ? ` le ${c.importe_le.replace('T', ' ').slice(0, 16)}` : ''}</dd>
        <dt class="text-muted-foreground">Contenu</dt><dd>{c.lignes} lignes, de {c.annees[0]} à {c.annees[1]}</dd>
        <dt class="text-muted-foreground">À surveiller</dt><dd>{c.provisoires} provisoires, {c.a_verifier} « à vérifier »</dd>
      </dl>
      <ol class="mt-4 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
        <li>Télécharger le fichier actuel.</li>
        <li>Dans Claude, coller le prompt et joindre le fichier.</li>
        <li>Importer ici le fichier rendu par Claude (il est contrôlé avant d'être gardé).</li>
      </ol>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <a href="/api/culture/fichier" class="inline-flex h-9 items-center rounded-lg border px-3 text-sm hover:bg-secondary">Télécharger le fichier</a>
        <Button variant="outline" size="sm" onclick={copier}>{copie ? 'Prompt copié' : 'Copier le prompt'}</Button>
        <label class="inline-flex h-9 cursor-pointer items-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground">
          Importer un fichier<input type="file" accept=".csv,text/csv" class="sr-only" onchange={importer} />
        </label>
        {#if c.source === 'importé'}<Button variant="ghost" size="sm" onclick={revenir}>Revenir à la version livrée</Button>{/if}
      </div>
      {#if message}<p class="mt-3 text-sm" role="status">{message}</p>{/if}
      <details class="mt-3 text-sm" bind:open={voirPrompt}>
        <summary class="cursor-pointer text-muted-foreground">Voir le prompt</summary>
        <pre class="mt-2 max-h-80 overflow-auto rounded-lg border bg-background p-3 text-xs whitespace-pre-wrap">{c.prompt}</pre>
      </details>
    </section>
  {/if}

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Règles</h2>
    <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
      <li>La une : le jour même, sinon la veille, la semaine, le mois — la portée est écrite au-dessus du titre.</li>
      <li>Drames (décès, attentats, catastrophes…) : jamais choisis seuls, sur aucun bloc ; visibles à la relecture avec leur raison.</li>
      <li>Textes en anglais : proposés en repli, jamais choisis seuls.</li>
      <li>L'année est toujours affichée ; l'âge en chiffres, jamais.</li>
      <li>Anniversaire à 14 jours ou moins du séjour : phrases proposées dans À traiter.</li>
    </ul>
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Journal</h2>
    {#if r.historique.length === 0}
      <p class="mt-1 text-sm text-muted-foreground">Rien pour l'instant.</p>
    {:else}
      <ul class="mt-2 grid gap-1 text-sm">
        {#each r.historique as h}
          <li class="flex gap-3"><span class="w-36 shrink-0 text-muted-foreground">{h.le.replace('T', ' ').slice(0, 16)}</span>
            <span>{GESTES[h.geste] ?? h.geste}{h.nom ? ' · ' + h.nom : ''}{h.detail ? ' · ' + h.detail : ''}</span></li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Gazette {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
