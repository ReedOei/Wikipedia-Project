for dir in $(ls "logs/"); do
    for innerdir in $(ls "logs/$dir/"); do
        charcount=$(wc -m logs/$dir/$innerdir/* | awk '{print $1}')

        if [ "$charcount" -eq 2 ]; then
            echo "The logs in 'logs/$dir/$innerdir' are empty, removing the folder."
            rm -rf "logs/$dir/$innerdir/"
        fi
    done
done
