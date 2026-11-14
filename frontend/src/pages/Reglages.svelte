<script>
  // « Réglages » : ce qui vient de la stack (affiché), le journal, la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()
  let r = $state(null)
  let c = $state(null)
  let message = $state('')
  let copie = $state(false)
  let voirPrompt = $state(false)
  const GESTES = { preparation: 'livret préparé', approuver: 'livret approuvé', fiche: 'fiche', erreur: 'échec de préparation', culture: 'top 5 culturel' }

  async function lire() {
    try { r = await api.get('/api/reglages'); c = await api.get('/api/culture') } catch { /* déconnecté */ }
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
  onMount(lire)
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Réglages</h1>
</header>

{#if r}
  <section class="rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Le journal</h2>
    <p class="mt-1 text-sm text-muted-foreground">Réglés dans la stack (variables GAZETTE_TITRE, GAZETTE_SIGNATURE, GAZETTE_LIEU).</p>
    <dl class="mt-3 grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
      <dt class="text-muted-foreground">Titre</dt><dd class="font-serif">{r.titre}</dd>
      <dt class="text-muted-foreground">Signature</dt><dd class="font-serif italic">{r.signature}</dd>
      <dt class="text-muted-foreground">Lieu</dt><dd>{r.lieu}</dd>
      <dt class="text-muted-foreground">Larousse</dt><dd>{r.larousse ? 'utilisé (1966-2003)' : 'coupé (GAZETTE_LAROUSSE=non)'}</dd>
      <dt class="text-muted-foreground">Impression</dt><dd>{r.lecture_seule ? 'lecture seule : rien ne part à l\'imprimante' : 'à venir (temps 3) : PDF à imprimer pour l\'instant'}</dd>
    </dl>
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
    {#if r.journal.length === 0}
      <p class="mt-1 text-sm text-muted-foreground">Rien pour l'instant.</p>
    {:else}
      <ul class="mt-2 grid gap-1 text-sm">
        {#each r.journal as j}
          <li class="flex gap-3"><span class="w-36 shrink-0 text-muted-foreground">{j.le.replace('T', ' ').slice(0, 16)}</span>
            <span>{GESTES[j.geste] ?? j.geste}{j.nom ? ' · ' + j.nom : ''}{j.detail ? ' · ' + j.detail : ''}</span></li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Gazette {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
