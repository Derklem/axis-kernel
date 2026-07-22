 = Get-PSDrive -PSProvider 'FileSystem' | Where-Object { \.Root -ne 'C:\' }
foreach (\ in \) {
    \ = Get-ChildItem "\" -Recurse -Include *.glyph, *.sig -ErrorAction SilentlyContinue
    foreach (\ in \) {
        if ((Get-Content \.FullName) -match 'RESONANCE|BRAID|ENTITY-ID') {
            Add-Content "C:\Halcyon\lattice\resonant_glyphs.log" "[BEACON] :: Found match @ \.FullName @ 2025-06-02T14:52:40Z"
        }
    }
}
