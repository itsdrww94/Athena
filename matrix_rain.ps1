$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "Green"
Clear-Host

$width = $Host.UI.RawUI.WindowSize.Width
$drops = New-Object int[] $width

for(;;) {
    for($i=0; $i -lt $width; $i++) {
        if($drops[$i] -gt 0) {
            $drops[$i]--
            if($drops[$i] -eq 0) {
                # Erase tail
                $pos = $Host.UI.RawUI.CursorPosition
                $pos.X = $i
                $pos.Y = 0 # Simple version, just keeps scrolling
            }
        } elseif((Get-Random -Max 100) -gt 95) {
            $drops[$i] = (Get-Random -Max 20) + 5
        }
    }
    
    $line = ""
    for($i=0; $i -lt $width; $i++) {
        if($drops[$i] -gt 0) {
            $char = [char]((Get-Random -Max 94) + 33)
            $line += $char
        } else {
            $line += " "
        }
    }
    Write-Host $line -ForegroundColor Green
    Start-Sleep -Milliseconds 50
}