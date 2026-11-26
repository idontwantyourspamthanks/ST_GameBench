require "json"
out = ARGV.map do |f|
  r = Hub::Ncmp::Parser.parse(File.binread(f))
  { file: File.basename(f), levels: r.levels.map { |l| { name: l.name, mission: l.mission, tower: l.tower, rows: l.rows, flags: l.record.getbyte(3), colours: l.colours, enemy_set: l.enemy_set, colour_scheme: l.colour_scheme, eye_design: l.eye_design, time_bcd: l.time_bcd, grid: l.grid } },
    playlists: r.playlists }
end
puts JSON.generate(out)
